"""IndiaWeatherBench auxiliary field acquisition: coarse H500 / T850 over the MCZ.

ARCHITECTURE.md Stage 1 lists "coarse H500 / T850 fields" as auxiliary inputs
alongside the index trajectory. DATA.md specifies IndiaWeatherBench (IMDAA,
0.12 deg) as the primary training data -- confirmed as the source here rather
than assumed; no other path is hardcoded.

Provenance (DISCUSSION D-11): HuggingFace `datasets/tungnd/IndiaWeatherBench`,
the paper authors' own distribution point. CC-BY-NC-SA-4.0, non-commercial (D-9).

Why range-reads instead of downloading (DISCUSSION D-8, D-12): the archive is
101 GB and there is no server-side subsetting. But the raw zarr chunks
`HGT`/`TMP_prl` as [183, 1, 64, 64] -- the LEVEL dimension is chunked at 1 --
so a single pressure level can be pulled without touching the other six.
Restricted to the MCZ box and the May-Sep window this is ~0.45 GB instead of
101 GB, and nothing is written to disk except the reduced daily series.

Read path per chunk: HTTP range GET -> zip local-header parse -> raw DEFLATE
inflate -> blosc decode -> numpy. The stdlib ZipFile object is not thread-safe
over a shared remote file, so the central directory is read once and the per-
chunk fetches are plain parallel range requests.
"""

from __future__ import annotations

import concurrent.futures as cf
import io
import json
import os
import struct
import zipfile
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests
from numcodecs import Blosc

HF_RAW_ZARR = (
    "https://huggingface.co/datasets/tungnd/IndiaWeatherBench/"
    "resolve/main/indiaweatherbench_raw.zarr.zip"
)
ZARR_ROOT = "indibench_raw.zarr"

# Pressure levels, in the order stored on the `isobaricInhPa` axis.
LEVELS_HPA = [925, 850, 700, 600, 500, 250, 50]
LEVEL_INDEX = {hpa: i for i, hpa in enumerate(LEVELS_HPA)}

# IWB native grid (verified 2026-09-07): 256x256 at 0.12 deg.
LAT0, DLAT, NLAT = 6.12, 0.12, 256
LON0, DLON, NLON = 66.60, 0.12, 256

UA = {"User-Agent": "VarshaSanket/0.1 (SIH26086 research prototype)"}


@dataclass(frozen=True)
class _Member:
    offset: int
    compress_size: int
    compress_type: int


def _grid_axis(a0: float, da: float, n: int) -> np.ndarray:
    return a0 + da * np.arange(n)


def _read_central_directory(url: str) -> tuple[dict, dict]:
    """Read the remote zip's central directory once; return (members, zmetadata)."""
    import fsspec

    fh = fsspec.filesystem("http").open(url, "rb")
    zf = zipfile.ZipFile(fh)
    members = {
        i.filename: _Member(i.header_offset, i.compress_size, i.compress_type)
        for i in zf.infolist()
    }
    zmeta = json.loads(zf.read(f"{ZARR_ROOT}/.zmetadata"))["metadata"]
    return members, zmeta


def _fetch_chunk(url: str, m: _Member, dtype: str, shape: list[int]) -> np.ndarray:
    """Range-GET one zip member, inflate, blosc-decode, reshape."""
    # Local header is 30 bytes + filename + extra; pad generously and slice so
    # this costs one round trip rather than two.
    pad = 512
    end = m.offset + 30 + pad + m.compress_size
    r = requests.get(
        url, headers={**UA, "Range": f"bytes={m.offset}-{end}"}, timeout=120
    )
    r.raise_for_status()
    buf = r.content
    if buf[:4] != b"PK\x03\x04":
        raise ValueError("not a zip local file header")
    fnlen, extralen = struct.unpack("<HH", buf[26:30])
    start = 30 + fnlen + extralen
    payload = buf[start : start + m.compress_size]
    if m.compress_type == zipfile.ZIP_DEFLATED:
        payload = zlib.decompress(payload, -15)
    raw = Blosc().decode(payload)
    return np.frombuffer(raw, dtype=np.dtype(dtype)).reshape(shape)


def _time_axis(url: str, members: dict, zmeta: dict) -> pd.DatetimeIndex:
    spec = zmeta["time/.zarray"]
    n, csize = spec["shape"][0], spec["chunks"][0]
    attrs = zmeta["time/.zattrs"]
    units = attrs["units"]  # "hours since 2000-01-01"
    origin = pd.Timestamp(units.split("since")[1].strip())
    out = []
    for ci in range((n + csize - 1) // csize):
        key = f"{ZARR_ROOT}/time/{ci}"
        arr = _fetch_chunk(url, members[key], spec["dtype"], [csize])
        out.append(arr)
    hours = np.concatenate(out)[:n]
    return pd.DatetimeIndex(origin + pd.to_timedelta(hours, unit="h"))


@dataclass(frozen=True)
class AuxFields:
    """Daily coarse H500 / T850 summaries over the monsoon core zone."""

    frame: pd.DataFrame
    source_url: str
    lat_bounds: tuple[float, float]
    lon_bounds: tuple[float, float]
    n_gridpoints: int
    bytes_fetched: int

    def describe(self) -> str:
        return (
            f"IWB aux fields | {self.frame.index.min().date()} -> {self.frame.index.max().date()} | "
            f"{len(self.frame)} days | cols {list(self.frame.columns)} | "
            f"MCZ {self.lat_bounds[0]:.2f}-{self.lat_bounds[1]:.2f}N "
            f"{self.lon_bounds[0]:.2f}-{self.lon_bounds[1]:.2f}E "
            f"({self.n_gridpoints} pts) | {self.bytes_fetched/1e6:.0f} MB fetched"
        )


def load_aux_fields(
    years: tuple[int, int],
    lat_bounds: tuple[float, float] = (18.0, 28.0),
    lon_bounds: tuple[float, float] = (65.0, 88.0),
    months: tuple[int, int] = (5, 9),
    cache_path: str = "data/cache/iwb_aux_h500_t850.parquet",
    max_workers: int = 12,
) -> AuxFields:
    """Daily MCZ-mean H500 and T850 (+ meridional T850 gradient) for `years`.

    Only chunks overlapping `months` are fetched. Spatial reduction is
    cos(lat)-weighted. The gradient term is (north half - south half) of the
    MCZ box, a standard proxy for the tropospheric temperature gradient that
    drives monsoon strength.
    """
    meta_path = cache_path + ".meta.json"
    if os.path.exists(cache_path):
        frame = pd.read_parquet(cache_path)
        # Carry the ORIGINAL fetch provenance forward. Returning placeholders
        # here made the run log report "-1 pts | 0 MB fetched" on any cached
        # run, which understates the real footprint of the data behind a
        # published number.
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                m = json.load(f)
            return AuxFields(
                frame,
                m["source_url"],
                tuple(m["lat_bounds"]),
                tuple(m["lon_bounds"]),
                m["n_gridpoints"],
                m["bytes_fetched"],
            )
        raise FileNotFoundError(
            f"{cache_path} exists but {meta_path} does not -- provenance for the "
            "cached fields is unknown. Delete the cache and refetch rather than "
            "reporting a number whose data footprint cannot be stated."
        )

    members, zmeta = _read_central_directory(HF_RAW_ZARR)
    times = _time_axis(HF_RAW_ZARR, members, zmeta)

    lats, lons = _grid_axis(LAT0, DLAT, NLAT), _grid_axis(LON0, DLON, NLON)
    lat_sel = np.where((lats >= lat_bounds[0]) & (lats <= lat_bounds[1]))[0]
    lon_sel = np.where((lons >= lon_bounds[0]) & (lons <= lon_bounds[1]))[0]

    spec = zmeta["HGT/.zarray"]
    ct, _, cy, cx = spec["chunks"]
    lat_chunks = sorted({int(i) // cy for i in lat_sel})
    lon_chunks = sorted({int(i) // cx for i in lon_sel})

    in_window = (times.month >= months[0]) & (times.month <= months[1])
    in_years = (times.year >= years[0]) & (times.year <= years[1])
    keep = np.where(in_window & in_years)[0]
    time_chunks = sorted({int(i) // ct for i in keep})

    jobs = []
    for var, level in (("HGT", 500), ("TMP_prl", 850)):
        li = LEVEL_INDEX[level]
        for tc in time_chunks:
            for yc in lat_chunks:
                for xc in lon_chunks:
                    jobs.append((var, level, tc, li, yc, xc))

    print(
        f"[iwb] {len(jobs)} chunks: {len(time_chunks)} time x "
        f"{len(lat_chunks)}x{len(lon_chunks)} spatial x 2 vars",
        flush=True,
    )

    results: dict[tuple, np.ndarray] = {}
    total_bytes = 0

    def work(job):
        var, level, tc, li, yc, xc = job
        key = f"{ZARR_ROOT}/{var}/{tc}.{li}.{yc}.{xc}"
        m = members[key]
        arr = _fetch_chunk(HF_RAW_ZARR, m, spec["dtype"], [ct, 1, cy, cx])
        return job, arr[:, 0, :, :], m.compress_size

    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for n, (job, arr, nbytes) in enumerate(ex.map(work, jobs), 1):
            results[job] = arr
            total_bytes += nbytes
            if n % 100 == 0:
                print(f"[iwb]   {n}/{len(jobs)} chunks", flush=True)

    # Assemble per time-chunk, reduce spatially, then concatenate.
    lat_off, lon_off = lat_chunks[0] * cy, lon_chunks[0] * cx
    loc_lat = lat_sel - lat_off
    loc_lon = lon_sel - lon_off
    w = np.cos(np.deg2rad(lats[lat_sel]))[:, None]
    mid = len(lat_sel) // 2

    rows = {}
    for var, level, col in (("HGT", 500, "h500"), ("TMP_prl", 850, "t850")):
        li = LEVEL_INDEX[level]
        series_vals, series_idx, north, south = [], [], [], []
        for tc in time_chunks:
            tiles = [
                np.concatenate(
                    [results[(var, level, tc, li, yc, xc)] for xc in lon_chunks], axis=2
                )
                for yc in lat_chunks
            ]
            block = np.concatenate(tiles, axis=1)  # (ct, lat, lon)
            block = block[:, loc_lat, :][:, :, loc_lon]

            t_idx = np.arange(tc * ct, min((tc + 1) * ct, len(times)))
            block = block[: len(t_idx)]

            ww = np.broadcast_to(w, block.shape[1:])
            series_vals.append((block * ww).sum(axis=(1, 2)) / ww.sum())
            north.append(
                (block[:, mid:, :] * ww[mid:, :]).sum(axis=(1, 2)) / ww[mid:, :].sum()
            )
            south.append(
                (block[:, :mid, :] * ww[:mid, :]).sum(axis=(1, 2)) / ww[:mid, :].sum()
            )
            series_idx.append(times[t_idx])

        idx = pd.DatetimeIndex(np.concatenate([i.values for i in series_idx]))
        rows[col] = pd.Series(np.concatenate(series_vals), index=idx)
        if col == "t850":
            rows["t850_grad"] = pd.Series(
                np.concatenate(north) - np.concatenate(south), index=idx
            )

    frame = pd.DataFrame(rows).sort_index()
    frame = frame[(frame.index.year >= years[0]) & (frame.index.year <= years[1])]
    frame = frame.resample("1D").mean().dropna(how="all")  # 6-hourly -> daily

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    frame.to_parquet(cache_path)

    out = AuxFields(
        frame=frame,
        source_url=HF_RAW_ZARR,
        lat_bounds=(float(lats[lat_sel].min()), float(lats[lat_sel].max())),
        lon_bounds=(float(lons[lon_sel].min()), float(lons[lon_sel].max())),
        n_gridpoints=len(lat_sel) * len(lon_sel),
        bytes_fetched=total_bytes,
    )
    with open(meta_path, "w") as f:
        json.dump(
            {
                "source_url": out.source_url,
                "lat_bounds": list(out.lat_bounds),
                "lon_bounds": list(out.lon_bounds),
                "n_gridpoints": out.n_gridpoints,
                "bytes_fetched": out.bytes_fetched,
                "chunks_fetched": len(jobs),
            },
            f,
            indent=2,
        )
    return out


if __name__ == "__main__":
    aux = load_aux_fields((2000, 2019))
    print(aux.describe())
    print(aux.frame.head())
    print(aux.frame.describe())

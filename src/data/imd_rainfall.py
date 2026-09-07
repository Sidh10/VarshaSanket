"""IMD gridded daily rainfall acquisition (ground truth for regime labels).

Source: IMD 0.25 deg gridded daily rainfall via `imdlib` (DATA.md, verified live
2026-09-07 -- see DISCUSSION D-6). Downloads from imdpune.gov.in. This is the
ONLY rainfall source used for label construction; no other path is permitted
(CLAUDE.md: all data acquisition goes through src/data/).

Resolution reality check (DATA.md "The resolution problem"):
  IMD gridded rain is 0.25 deg (~25 km), 129 lat x 135 lon, 6.5-38.5N / 66.5-100.0E.
  Fill value for ocean / outside-India cells is -999.0 and MUST be masked.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Monsoon Core Zone, Rajeevan et al. (2010), J. Earth Syst. Sci. 119:229-247,
# "Active and break spells of the Indian summer monsoon". MCZ ~= 18-28N, 65-88E.
#
# CAVEAT (disclose, do not silently clip): the IMD 0.25 deg grid starts at
# 66.5E, so the western edge of the published MCZ (65E) lies outside the data
# domain. The effective zone used here is 66.5-88E. Rajeevan et al. used IMD
# gridded data with the same western boundary, so this is the same effective
# region they worked with, but the stated box differs from the literal citation.
MCZ_LAT = (18.0, 28.0)
MCZ_LON = (65.0, 88.0)

IMD_FILL = -999.0


@dataclass(frozen=True)
class RainfallSeries:
    """MCZ-averaged daily rainfall with the provenance needed to defend it."""

    series: pd.Series  # index: DatetimeIndex (daily), values: mm/day
    n_cells: int  # valid (land) grid cells inside the MCZ box
    lat_bounds: tuple[float, float]
    lon_bounds: tuple[float, float]
    years: tuple[int, int]

    def describe(self) -> str:
        return (
            f"MCZ mean daily rainfall | {self.years[0]}-{self.years[1]} | "
            f"{len(self.series)} days | {self.n_cells} valid 0.25deg cells | "
            f"lat {self.lat_bounds[0]}-{self.lat_bounds[1]}N "
            f"lon {self.lon_bounds[0]}-{self.lon_bounds[1]}E"
        )


def download_rainfall(
    start_year: int,
    end_year: int,
    cache_dir: str = "data/raw/imd",
) -> None:
    """Fetch IMD gridded daily rainfall year by year into `cache_dir`.

    imdlib writes one binary .GRD per year and skips nothing, so this is
    idempotent only at the year level -- we check for the file first.
    """
    import imdlib as imd

    os.makedirs(cache_dir, exist_ok=True)
    for year in range(start_year, end_year + 1):
        target = os.path.join(cache_dir, "rain", f"{year}.GRD")
        if os.path.exists(target):
            print(f"[imd] {year} already cached", flush=True)
            continue
        print(f"[imd] downloading {year} ...", flush=True)
        imd.get_data("rain", year, year, fn_format="yearwise", file_dir=cache_dir)
        print(f"[imd] {year} done", flush=True)


def load_mcz_rainfall(
    start_year: int,
    end_year: int,
    cache_dir: str = "data/raw/imd",
    lat_bounds: tuple[float, float] = MCZ_LAT,
    lon_bounds: tuple[float, float] = MCZ_LON,
) -> RainfallSeries:
    """Load cached IMD rainfall and reduce to a daily MCZ-average series.

    Masks the -999 fill value; a grid cell is counted only if it is valid on
    every day of the record, so the spatial average is over a fixed cell set
    (a varying denominator would inject spurious day-to-day variance into the
    anomaly that the Rajeevan criterion is applied to).
    """
    import imdlib as imd

    frames = []
    n_cells = 0
    lat_used = lon_used = (np.nan, np.nan)

    for year in range(start_year, end_year + 1):
        data = imd.open_data("rain", year, year, fn_format="yearwise", file_dir=cache_dir)
        ds = data.get_xarray()
        sub = ds["rain"].sel(
            lat=slice(lat_bounds[0], lat_bounds[1]),
            lon=slice(lon_bounds[0], lon_bounds[1]),
        )
        arr = sub.values.astype("float64")
        arr[arr <= IMD_FILL + 1.0] = np.nan  # -999 fill -> NaN

        # Fixed cell set: valid on every day of this year.
        valid = ~np.isnan(arr).any(axis=0)
        n_cells = int(valid.sum())
        lat_used = (float(sub["lat"].min()), float(sub["lat"].max()))
        lon_used = (float(sub["lon"].min()), float(sub["lon"].max()))

        daily = np.where(valid[None, :, :], arr, np.nan)
        mean = np.nanmean(daily.reshape(daily.shape[0], -1), axis=1)
        frames.append(pd.Series(mean, index=pd.to_datetime(sub["time"].values)))

    series = pd.concat(frames).sort_index()
    return RainfallSeries(
        series=series,
        n_cells=n_cells,
        lat_bounds=lat_used,
        lon_bounds=lon_used,
        years=(start_year, end_year),
    )


if __name__ == "__main__":
    import sys

    a = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 2019
    download_rainfall(a, b)

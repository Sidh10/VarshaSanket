"""MCZ reconciliation: IMD sub-divisions <-> the Rajeevan monsoon core zone.

THE PROBLEM THIS EXISTS TO NOT PAPER OVER
-----------------------------------------
The Rajeevan et al. (2010) monsoon core zone is a lat/lon box: **18-28N, 65-88E**.
IMD bulletins do not talk in lat/lon -- they name sub-divisions and states
("East Madhya Pradesh", "Vidarbha", "Odisha"). Those two do not line up.

It is tempting to declare "Central India ~ the MCZ" and move on. That would be
wrong, and this module exists to show *how* wrong with real geometry rather than
asserting it either way. Overlap is computed from IMD's own sub-division polygons
(the 36-feature GeoJSON served by `index_rainfall_subdiv.php`) intersected with
the MCZ box, so the mismatch is a measured number, not an opinion.

The headline result is reported by `mcz_overlap_table()` and it does not flatter
the "Central India proxy" shortcut: the MCZ spans sub-divisions belonging to
THREE different IMD homogeneous regions (Central India, North West India, and
East & North East India), and several Central India sub-divisions lie largely
OUTSIDE the box. Using Central India as a stand-in would both include area the
MCZ excludes and exclude area the MCZ includes.

WHAT IS AUTHORED HERE
---------------------
`MCZ_LAT`/`MCZ_LON` come from the published Rajeevan definition. Everything else
-- the overlap threshold used to call a sub-division "MCZ-relevant", and the
decision to weight coverage by intersected area -- is ours. Both are exposed as
parameters rather than baked in.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import pandas as pd
from shapely.geometry import box, shape
from shapely.ops import unary_union

# Rajeevan et al. (2010), J. Earth Syst. Sci. 119:229-247.
MCZ_LAT = (18.0, 28.0)
MCZ_LON = (65.0, 88.0)

GEOJSON_PATH = "data/raw/geo/sd_boundary_rainfall.json"
GEOJSON_URL = (
    "https://mausam.imd.gov.in/imd_latest/contents/"
    "district_shapefiles/sd_boundary_rainfall.json"
)


def _load_subdivisions(path: str = GEOJSON_PATH) -> list[dict]:
    """IMD's own 36 meteorological sub-division polygons.

    Carries boundaries + names only -- despite the filename it contains no
    rainfall (verified, D-15 addendum 4).
    """
    if not os.path.exists(path):
        import requests

        os.makedirs(os.path.dirname(path), exist_ok=True)
        r = requests.get(
            GEOJSON_URL,
            headers={"User-Agent": "VarshaSanket/0.1 (SIH26086 research prototype)"},
            timeout=180,
        )
        r.raise_for_status()
        open(path, "wb").write(r.content)
    return json.load(open(path, encoding="utf-8"))["features"]


def mcz_overlap_table(path: str = GEOJSON_PATH) -> pd.DataFrame:
    """Per sub-division: what fraction of its area lies inside the MCZ box.

    Returns columns: subdivision, region, area, mcz_area, frac_in_mcz.
    `frac_in_mcz` is computed in degree-space (adequate for a relative
    comparison at this latitude band; we are not reporting absolute km^2).
    """
    mcz = box(MCZ_LON[0], MCZ_LAT[0], MCZ_LON[1], MCZ_LAT[1])
    rows = []
    for f in _load_subdivisions(path):
        try:
            geom = shape(f["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
        except Exception:
            continue
        p = f.get("properties", {})
        inter = geom.intersection(mcz)
        rows.append(
            {
                "subdivision": (p.get("subdivisio") or p.get("name") or "").strip(),
                "region": (p.get("region_cod") or "").strip(),
                "area": geom.area,
                "mcz_area": inter.area,
                "frac_in_mcz": (inter.area / geom.area) if geom.area else 0.0,
            }
        )
    df = pd.DataFrame(rows).sort_values("frac_in_mcz", ascending=False)
    return df.reset_index(drop=True)


def mcz_subdivisions(threshold: float = 0.25, path: str = GEOJSON_PATH) -> pd.DataFrame:
    """Sub-divisions counted as MCZ-relevant.

    `threshold` is AUTHORED, not from the literature -- 0.25 means "at least a
    quarter of the sub-division lies inside the Rajeevan box". Exposed as a
    parameter precisely so the sensitivity of any downstream result to this
    choice can be checked rather than assumed away.
    """
    df = mcz_overlap_table(path)
    return df[df["frac_in_mcz"] >= threshold].reset_index(drop=True)


@dataclass(frozen=True)
class MczCoverage:
    n_mcz_subdivisions: int
    n_mentioned: int
    frac_mentioned: float          # unweighted: fraction of MCZ subdivisions named
    frac_area_mentioned: float     # weighted by intersected area -- the honest one
    mentioned: tuple[str, ...]
    missing: tuple[str, ...]


def _alias_patterns(name: str) -> str:
    """Bulletins write sub-division names loosely. Build a tolerant pattern."""
    n = name.lower().strip()
    n = re.sub(r"\s*&\s*", " and ", n)
    n = re.sub(r"[^a-z ]", " ", n)
    parts = [p for p in n.split() if p not in ("and", "of", "the")]
    if not parts:
        return re.escape(name)
    # require the distinctive token(s); allow intervening words
    core = r"\s+(?:\w+\s+){0,2}".join(re.escape(p) for p in parts[:2])
    return core


def coverage_for_text(
    text: str, threshold: float = 0.25, path: str = GEOJSON_PATH
) -> MczCoverage:
    """How much of the MCZ does this bulletin's regional breakdown actually name?

    This is the number that must be disclosed rather than smoothed over. A
    bulletin naming only "Central India" scores far below one that enumerates
    East MP, Chhattisgarh, Vidarbha, Odisha and Jharkhand -- and the difference
    matters, because a trough-position statement attached to the former is a
    much weaker claim about the core zone than the latter.
    """
    mcz = mcz_subdivisions(threshold, path)
    hits, misses, area_hit = [], [], 0.0
    for _, r in mcz.iterrows():
        pat = _alias_patterns(r["subdivision"])
        if re.search(pat, text, re.I):
            hits.append(r["subdivision"])
            area_hit += r["mcz_area"]
        else:
            misses.append(r["subdivision"])
    total_area = float(mcz["mcz_area"].sum()) or 1.0
    return MczCoverage(
        n_mcz_subdivisions=len(mcz),
        n_mentioned=len(hits),
        frac_mentioned=len(hits) / max(len(mcz), 1),
        frac_area_mentioned=area_hit / total_area,
        mentioned=tuple(hits),
        missing=tuple(misses),
    )


def region_proxy_error(threshold: float = 0.25, path: str = GEOJSON_PATH) -> str:
    """Quantify the error in using IMD's 'Central India' region as an MCZ proxy.

    Reported as text because the point is the disclosure, not a scalar to
    optimise. Shows both directions of the mismatch.
    """
    df = mcz_overlap_table(path)
    mcz = df[df["frac_in_mcz"] >= threshold]
    central = df[df["region"].str.upper().str.contains("CENTRAL", na=False)]

    mcz_names = set(mcz["subdivision"])
    cen_names = set(central["subdivision"])
    in_mcz_not_central = sorted(mcz_names - cen_names)
    in_central_not_mcz = sorted(cen_names - mcz_names)

    regions = mcz["region"].value_counts().to_dict()
    lines = [
        f"MCZ box {MCZ_LAT[0]}-{MCZ_LAT[1]}N {MCZ_LON[0]}-{MCZ_LON[1]}E; "
        f"threshold frac_in_mcz >= {threshold}",
        f"MCZ-relevant sub-divisions: {len(mcz_names)}",
        f"  spanning IMD homogeneous regions: {regions}",
        f"IMD 'Central India' sub-divisions: {len(cen_names)}",
        f"  in MCZ but NOT Central India ({len(in_mcz_not_central)}): {in_mcz_not_central}",
        f"  in Central India but NOT MCZ ({len(in_central_not_mcz)}): {in_central_not_mcz}",
    ]
    return "\n".join(lines)

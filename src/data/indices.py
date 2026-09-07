"""Teleconnection index acquisition: Nino3.4 (ENSO), DMI (IOD), RMM1/RMM2 (MJO).

Every URL here was hit live and confirmed returning data (DISCUSSION D-7, D-13).
Providers are NOT interchangeable and are NOT all NOAA CPC -- that was the error
corrected in D-7:

  Nino3.4  -> NOAA CPC        weekly  (OISST, wksst9120.for)
  DMI      -> NOAA PSL        monthly (HadISST, dmi.had.long.data)   [not CPC, not BOM -- D-13]
  RMM1/2   -> Australian BOM  daily   (Wheeler-Hendon rmm.74toRealtime.txt)

Cadence is mixed on purpose and is disclosed rather than hidden: the t-30 -> t
trajectory features treat DMI as near-constant within most windows because it
genuinely is monthly. See src/features/trajectory.py.

NEVER add an api.imd.gov.in endpoint here (RESEARCH.md, Debunked).
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "VarshaSanket/0.1 (SIH26086 research prototype)"}

NINO34_WEEKLY_URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
DMI_MONTHLY_URL = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
RMM_DAILY_URL = "https://www.bom.gov.au/clim_data/IDCKGEM000/rmm.74toRealtime.txt"

RMM_MISSING = 1e30  # file states "Missing Value= 1.E36 or 999"


@dataclass(frozen=True)
class IndexBundle:
    """Raw index series at their native cadences, plus provenance."""

    nino34: pd.Series  # weekly Nino3.4 SST anomaly (degC)
    dmi: pd.Series  # monthly Dipole Mode Index (degC)
    rmm1: pd.Series  # daily RMM1
    rmm2: pd.Series  # daily RMM2
    sources: dict[str, str]

    def describe(self) -> str:
        rows = [
            f"  nino34 {len(self.nino34):>6} pts  {self.nino34.index.min().date()} -> {self.nino34.index.max().date()}  (weekly, NOAA CPC)",
            f"  dmi    {len(self.dmi):>6} pts  {self.dmi.index.min().date()} -> {self.dmi.index.max().date()}  (monthly, NOAA PSL)",
            f"  rmm1   {len(self.rmm1):>6} pts  {self.rmm1.index.min().date()} -> {self.rmm1.index.max().date()}  (daily, BOM)",
            f"  rmm2   {len(self.rmm2):>6} pts  {self.rmm2.index.min().date()} -> {self.rmm2.index.max().date()}  (daily, BOM)",
        ]
        return "\n".join(rows)


def _fetch(url: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1]))
    if os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read()
    resp = requests.get(url, headers=UA, timeout=60)
    resp.raise_for_status()
    open(path, "w", encoding="utf-8").write(resp.text)
    return resp.text


def fetch_nino34_weekly(cache_dir: str = "data/raw/indices") -> pd.Series:
    """Weekly Nino3.4 SST anomaly from NOAA CPC (OISST, 1991-2020 base).

    Fixed-width-ish file where SST and anomaly can run together ("26.5-0.2"),
    so numbers are extracted by regex rather than whitespace split. Column
    order per header: Nino1+2, Nino3, Nino34, Nino4 -- each SST then SSTA.
    Nino3.4 anomaly is therefore the 6th number on the line (index 5).
    """
    text = _fetch(NINO34_WEEKLY_URL, cache_dir)
    dates, vals = [], []
    for line in text.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)", line)
        if not m:
            continue
        nums = re.findall(r"-?\d+\.\d+", m.group(2))
        if len(nums) < 6:
            continue
        dates.append(pd.to_datetime(m.group(1), format="%d%b%Y"))
        vals.append(float(nums[5]))
    return pd.Series(vals, index=pd.DatetimeIndex(dates), name="nino34").sort_index()


def fetch_dmi_monthly(cache_dir: str = "data/raw/indices") -> pd.Series:
    """Monthly Dipole Mode Index from NOAA PSL (HadISST-based, 1870-present).

    Layout: first line is "<start_year> <end_year>", then one row per year with
    12 monthly values, then free-text trailer lines. Missing values are large
    negatives (-9999 style); anything below -90 is treated as missing.
    Values are timestamped at month start.
    """
    text = _fetch(DMI_MONTHLY_URL, cache_dir)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    y0, y1 = (int(x) for x in lines[0].split()[:2])
    dates, vals = [], []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) < 13:
            continue
        try:
            year = int(parts[0])
        except ValueError:
            continue
        if not (y0 <= year <= y1):
            continue
        for month, raw in enumerate(parts[1:13], start=1):
            try:
                v = float(raw)
            except ValueError:
                continue
            dates.append(pd.Timestamp(year=year, month=month, day=1))
            vals.append(np.nan if v < -90 else v)
    return pd.Series(vals, index=pd.DatetimeIndex(dates), name="dmi").sort_index()


def fetch_rmm_daily(cache_dir: str = "data/raw/indices") -> tuple[pd.Series, pd.Series]:
    """Daily RMM1/RMM2 (Wheeler-Hendon MJO index) from the Australian BOM.

    Columns: year, month, day, RMM1, RMM2, phase, amplitude, <method tag>.
    Missing sentinel is 1.E36 or 999 per the file header.
    """
    text = _fetch(RMM_DAILY_URL, cache_dir)
    dates, r1, r2 = [], [], []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            a, b = float(parts[3]), float(parts[4])
        except ValueError:
            continue  # header lines
        if abs(a) > RMM_MISSING or abs(b) > RMM_MISSING or a == 999 or b == 999:
            a = b = np.nan
        dates.append(pd.Timestamp(year=y, month=m, day=d))
        r1.append(a)
        r2.append(b)
    idx = pd.DatetimeIndex(dates)
    return (
        pd.Series(r1, index=idx, name="rmm1").sort_index(),
        pd.Series(r2, index=idx, name="rmm2").sort_index(),
    )


def load_indices(cache_dir: str = "data/raw/indices") -> IndexBundle:
    n34 = fetch_nino34_weekly(cache_dir)
    dmi = fetch_dmi_monthly(cache_dir)
    rmm1, rmm2 = fetch_rmm_daily(cache_dir)
    return IndexBundle(
        nino34=n34,
        dmi=dmi,
        rmm1=rmm1,
        rmm2=rmm2,
        sources={
            "nino34": NINO34_WEEKLY_URL,
            "dmi": DMI_MONTHLY_URL,
            "rmm1/rmm2": RMM_DAILY_URL,
        },
    )


if __name__ == "__main__":
    b = load_indices()
    print("Loaded teleconnection indices:")
    print(b.describe())
    for k, v in b.sources.items():
        print(f"  source[{k}] = {v}")
    print("\nnino34 tail:\n", b.nino34.tail(3))
    print("\ndmi tail:\n", b.dmi.tail(3))
    print("\nrmm1 tail:\n", b.rmm1.tail(3))

"""Seasonal-scale ENSO/IOD state and seasonal rainfall outcome, one row per year.

WHY EVERYTHING HERE IS SEASONAL, AND WHY THAT IS THE WHOLE POINT
----------------------------------------------------------------
D-14 tested whether *within-season* index trajectories (t-30 -> t lags of
Nino3.4, DMI, RMM1/RMM2) predict the *sub-seasonal* regime at 1-4 week lead.
They do not: BSS vs climatology was -0.034 / -0.014 / -0.057 / +0.009, and a
linear reference model failed identically.

This module deliberately operates at a different scale, on a different claim:
ENSO/IOD modulation of **seasonal total** monsoon rainfall. That is a separate,
long-established relationship, and testing it is not a re-run of D-14.

To keep the two apart, this module computes **one value per year** and offers no
way to ask a week-specific question. There is no weekly resampling, no lag
construction, no within-season trajectory. If a caller needs a week-specific
ENSO/IOD distance, this module cannot supply it -- that is intentional, because
that quantity is exactly the falsified D-14 claim wearing a different label.

TWO SEASONAL WINDOWS, AND THE HONEST DIFFERENCE BETWEEN THEM
------------------------------------------------------------
  * `jjas`  -- Jun-Sep mean, CONCURRENT with the rainfall being explained.
               Diagnostic only. It is not knowable before the season starts, so
               it cannot support an operational claim. It answers "is there a
               relationship at all?"
  * `mam`   -- Mar-May mean, available BEFORE monsoon onset. This is the
               operationally usable one.

Both are computed and both must be reported. Quoting the concurrent number
without the pre-season one would overstate what the system could actually do.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data.imd_rainfall import load_mcz_rainfall
from src.data.indices import load_indices

JJAS_MONTHS = (6, 9)
MAM_MONTHS = (3, 5)


@dataclass(frozen=True)
class SeasonalTable:
    """One row per year. Index = year."""

    frame: pd.DataFrame  # nino34_jjas, dmi_jjas, nino34_mam, dmi_mam, rain_total, rain_anom
    years: tuple[int, int]

    def describe(self) -> str:
        f = self.frame
        return (
            f"seasonal state | {self.years[0]}-{self.years[1]} | {len(f)} years\n"
            f"  nino34 JJAS  mean {f.nino34_jjas.mean():+.2f}  sd {f.nino34_jjas.std():.2f}"
            f"   range [{f.nino34_jjas.min():+.2f}, {f.nino34_jjas.max():+.2f}]\n"
            f"  dmi    JJAS  mean {f.dmi_jjas.mean():+.2f}  sd {f.dmi_jjas.std():.2f}"
            f"   range [{f.dmi_jjas.min():+.2f}, {f.dmi_jjas.max():+.2f}]\n"
            f"  MCZ JJAS total rainfall  mean {f.rain_total.mean():.0f} mm  "
            f"sd {f.rain_total.std():.0f} mm"
        )


def _season_mean(s: pd.Series, months: tuple[int, int], year: int) -> float:
    m = s[(s.index.year == year) & (s.index.month >= months[0]) & (s.index.month <= months[1])]
    return float(m.mean()) if len(m) else np.nan


def build_seasonal_table(years: tuple[int, int]) -> SeasonalTable:
    """Seasonal ENSO/IOD state and seasonal MCZ rainfall, one row per year."""
    idx = load_indices()
    rain = load_mcz_rainfall(*years)

    rows = []
    for y in range(years[0], years[1] + 1):
        r = rain.series[
            (rain.series.index.year == y)
            & (rain.series.index.month >= JJAS_MONTHS[0])
            & (rain.series.index.month <= JJAS_MONTHS[1])
        ]
        rows.append(
            {
                "year": y,
                "nino34_jjas": _season_mean(idx.nino34, JJAS_MONTHS, y),
                "dmi_jjas": _season_mean(idx.dmi, JJAS_MONTHS, y),
                "nino34_mam": _season_mean(idx.nino34, MAM_MONTHS, y),
                "dmi_mam": _season_mean(idx.dmi, MAM_MONTHS, y),
                "rain_total": float(r.sum()),
                "n_days": int(len(r)),
            }
        )
    f = pd.DataFrame(rows).set_index("year")
    f["rain_anom"] = (f.rain_total - f.rain_total.mean()) / f.rain_total.std()
    return SeasonalTable(frame=f, years=years)


def tercile_labels(rain_total: pd.Series, exclude_year: int | None = None) -> pd.Series:
    """Classify each year's seasonal rainfall as dry / normal / wet.

    Tercile boundaries are computed EXCLUDING `exclude_year` when given, so that
    in a leave-one-year-out fold the held-out year does not help define the
    category it is then scored against. This is the seasonal-scale analogue of
    the label-leakage check in D-14 and it is not optional.
    """
    pool = rain_total.drop(index=exclude_year) if exclude_year is not None else rain_total
    lo, hi = pool.quantile([1 / 3, 2 / 3])
    return rain_total.map(lambda v: "dry" if v <= lo else ("wet" if v >= hi else "normal"))


TERCILES = ("dry", "normal", "wet")

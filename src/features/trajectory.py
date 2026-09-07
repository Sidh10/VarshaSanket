"""Index-trajectory features: t-30 -> t lags for Nino3.4, DMI, RMM1/RMM2 (+ aux fields).

ARCHITECTURE.md Stage 1: "uses the *recent trajectory* of indices, not forecast
indices. This keeps the system self-contained -- we don't inherit another
model's forecast error, and we don't depend on any restricted data feed."

Two things this module is careful about, because both are ways to manufacture
fake skill:

1. PUBLICATION LATENCY. An index value is not usable the instant it is dated.
   Each source is shifted by a conservative publication lag so that features
   at issue time t use only what a real operator would have had at t:

     Nino3.4  weekly  -> 7 days   (CPC posts the week's value the following week)
     DMI      monthly -> 30 days  (PSL monthly product)
     RMM1/2   daily   -> 2 days   (BOM near-real-time)
     H500/T850        -> 1 day    (analysis fields)

   These are assumptions, stated so they can be challenged. They are
   deliberately conservative -- erring toward LESS information, not more.

2. MIXED CADENCE IS NOT HIDDEN (DISCUSSION D-7, D-13). Nino3.4 is weekly and
   DMI is monthly, so their "t-30 -> t" trajectory is genuinely coarse: DMI is
   near-constant inside most 30-day windows and its delta terms carry little
   information. Only RMM is truly daily. Forward-filling makes the frame
   rectangular; it does not create information, and the delta features will
   show that honestly rather than implying daily resolution we do not have.

CAVEAT on the auxiliary fields: IMDAA is a *reanalysis*. Operationally the
equivalent input would be NCMRWF's operational analysis, which is available in
near-real time but is not identical in quality to the reanalysis. Using
reanalysis fields at t in a backtest is standard practice and is not temporal
leakage (the fields describe time t, not the future), but it does assume an
analysis of comparable quality is available operationally.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PUBLICATION_LAG_DAYS = {
    "nino34": 7,
    "dmi": 30,
    "rmm": 2,
    "aux": 1,
}

TRAJECTORY_LAGS = [0, 5, 10, 15, 20, 25, 30]  # days back from issue time t


@dataclass(frozen=True)
class FeatureMatrix:
    X: pd.DataFrame
    publication_lags: dict[str, int]
    lags_used: list[int]

    def describe(self) -> str:
        return (
            f"features | {self.X.shape[0]} issue dates x {self.X.shape[1]} columns | "
            f"{self.X.index.min().date()} -> {self.X.index.max().date()}\n"
            f"  trajectory lags (days): {self.lags_used}\n"
            f"  publication lags applied: {self.publication_lags}"
        )


def _to_daily(s: pd.Series, index: pd.DatetimeIndex, lag_days: int) -> pd.Series:
    """Resample a native-cadence series onto `index`, respecting publication lag.

    ffill only ever propagates a value FORWARD in time, so no future value can
    reach an earlier date. The extra `lag_days` shift then removes values that
    were dated before t but not yet published at t.
    """
    daily = s.reindex(s.index.union(index)).sort_index().ffill().reindex(index)
    return daily.shift(lag_days)


def build_features(
    indices,
    aux: pd.DataFrame,
    issue_dates: pd.DatetimeIndex,
    lags: list[int] = TRAJECTORY_LAGS,
) -> FeatureMatrix:
    """Construct the t-30 -> t trajectory feature matrix at each issue date."""
    span = pd.date_range(issue_dates.min() - pd.Timedelta(days=120), issue_dates.max())

    n34 = _to_daily(indices.nino34, span, PUBLICATION_LAG_DAYS["nino34"])
    dmi = _to_daily(indices.dmi, span, PUBLICATION_LAG_DAYS["dmi"])
    r1 = _to_daily(indices.rmm1, span, PUBLICATION_LAG_DAYS["rmm"])
    r2 = _to_daily(indices.rmm2, span, PUBLICATION_LAG_DAYS["rmm"])
    amp = np.sqrt(r1**2 + r2**2)

    aux_d = {
        c: _to_daily(aux[c], span, PUBLICATION_LAG_DAYS["aux"]) for c in aux.columns
    }

    cols: dict[str, pd.Series] = {}

    def at(s: pd.Series, lag: int) -> pd.Series:
        return s.shift(lag).reindex(issue_dates)

    # --- MJO: genuinely daily, so the full trajectory is meaningful.
    for lag in lags:
        cols[f"rmm1_lag{lag}"] = at(r1, lag)
        cols[f"rmm2_lag{lag}"] = at(r2, lag)
    for lag in [0, 10, 20, 30]:
        cols[f"mjo_amp_lag{lag}"] = at(amp, lag)
    # Eastward propagation: signed change in RMM phase angle over 10 and 20 days.
    #
    # Computed as a LOCAL circular difference, atan2(sin(da), cos(da)), NOT via
    # np.unwrap. unwrap is a cumulative operation, so a single missing day
    # poisons every value after it -- and the BOM record does have gaps (290
    # missing days). This form is wrapped to (-pi, pi] by construction and is
    # NaN only where its own two inputs are NaN.
    ang = np.arctan2(r2, r1)
    for lag in (10, 20):
        da = ang - ang.shift(lag)
        cols[f"mjo_phase_rate_{lag}"] = np.arctan2(np.sin(da), np.cos(da)).reindex(
            issue_dates
        )

    # --- ENSO: weekly. Level + slow trend only; daily lags would be fiction.
    for lag in [0, 15, 30]:
        cols[f"nino34_lag{lag}"] = at(n34, lag)
    cols["nino34_d15"] = at(n34, 0) - at(n34, 15)
    cols["nino34_d30"] = at(n34, 0) - at(n34, 30)

    # --- IOD: monthly. Level + 60d trend; a 30d delta is mostly zero by design.
    for lag in [0, 30, 60]:
        cols[f"dmi_lag{lag}"] = at(dmi, lag)
    cols["dmi_d30"] = at(dmi, 0) - at(dmi, 30)
    cols["dmi_d60"] = at(dmi, 0) - at(dmi, 60)

    # --- Auxiliary analysis fields: daily.
    for name, s in aux_d.items():
        cols[f"{name}_lag0"] = at(s, 0)
        cols[f"{name}_mean10"] = s.rolling(10).mean().reindex(issue_dates)
        cols[f"{name}_d30"] = at(s, 0) - at(s, 30)

    # --- Seasonal cycle. Included deliberately: the climatology baseline has
    # the same information, so any margin over it must come from the indices.
    doy = issue_dates.dayofyear.values
    cols["doy_sin"] = pd.Series(np.sin(2 * np.pi * doy / 365.25), index=issue_dates)
    cols["doy_cos"] = pd.Series(np.cos(2 * np.pi * doy / 365.25), index=issue_dates)

    X = pd.DataFrame(cols, index=issue_dates)
    return FeatureMatrix(X=X, publication_lags=dict(PUBLICATION_LAG_DAYS), lags_used=lags)


INDEX_FEATURE_PREFIXES = ("rmm1_", "rmm2_", "mjo_", "nino34_", "dmi_")
AUX_FEATURE_PREFIXES = ("h500_", "t850_")
SEASONAL_FEATURES = ("doy_sin", "doy_cos")

"""Stage 1 validation harness. THE ONLY PLACE ACCURACY METRICS ARE COMPUTED.

Implements docs/VERIFICATION.md for the Regime Forecaster:

  1. Leave-one-year-out across all 20 years -- never a single test year (D-E).
  2. Nothing from the held-out year touches the fold: not the model, not the
     climatology baseline, not the label climatology.
  3. NO feature selection happens anywhere, at any level. The feature set is
     fixed a priori in src/features/trajectory.py. Michaelsen (1987) showed
     predictor screening injects 0.36-0.71 of artificial skill -- far more than
     coefficient fitting -- so the safest defence is to do no screening at all.

     Model CAPACITY is selected, but only by an inner GroupKFold over the
     training years inside `RegimeForecaster.fit`, which the backtest only ever
     hands training-fold data. The held-out year is never seen. This is
     deliberate: leaving capacity pinned to an arbitrary guess would understate
     achievable skill, and reporting an under-powered model as the ceiling is
     as misleading as reporting an over-fitted one.
  4. Every figure is reported against climatology AND persistence.
  5. Event counts are stated with every score.
  6. Uncertainty is block-bootstrapped over YEARS, not days. Days inside a
     monsoon spell are strongly autocorrelated; a day-level CI would be
     dishonestly narrow. The independent unit is the year, and with 20 of them
     the interval is wide. That width is the real answer, not a presentation
     problem to be smoothed over.

The climatology-collapse test (VERIFICATION.md, "the sanity check that matters
most") is implemented as `seasonal_only`: the same forecaster fitted on the
day-of-year features alone. If the full model does not beat it, the indices are
contributing nothing and the pipeline has collapsed to climatology.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.features.labels import CLASSES
from src.models.regime_forecaster import RegimeForecaster, make_future_target


def multiclass_brier(proba: pd.DataFrame, truth: pd.Series) -> float:
    """Mean over samples of sum_k (p_k - o_k)^2. Range [0, 2]. Lower is better."""
    common = proba.index.intersection(truth.dropna().index)
    p = proba.loc[common, CLASSES].to_numpy(dtype=float)
    o = np.zeros_like(p)
    for j, c in enumerate(CLASSES):
        o[:, j] = (truth.loc[common] == c).to_numpy(dtype=float)
    ok = ~np.isnan(p).any(axis=1)
    return float(((p[ok] - o[ok]) ** 2).sum(axis=1).mean())


def brier_by_sample(proba: pd.DataFrame, truth: pd.Series) -> pd.Series:
    common = proba.index.intersection(truth.dropna().index)
    p = proba.loc[common, CLASSES].to_numpy(dtype=float)
    o = np.zeros_like(p)
    for j, c in enumerate(CLASSES):
        o[:, j] = (truth.loc[common] == c).to_numpy(dtype=float)
    return pd.Series(((p - o) ** 2).sum(axis=1), index=common)


def binary_brier(proba: pd.DataFrame, truth: pd.Series, cls: str) -> float:
    """One-vs-rest Brier score for a single regime class."""
    common = proba.index.intersection(truth.dropna().index)
    p = proba.loc[common, cls].to_numpy(dtype=float)
    o = (truth.loc[common] == cls).to_numpy(dtype=float)
    ok = ~np.isnan(p)
    return float(((p[ok] - o[ok]) ** 2).mean())


def climatology_proba(
    y_train: pd.Series, issue_dates: pd.DatetimeIndex, halfwindow: int = 7
) -> pd.DataFrame:
    """Day-of-year conditional climatological regime frequency.

    This is the baseline the Phase 1 gate names. It is the STRICTER of the two
    obvious choices -- it knows the seasonal progression of regime frequency
    through Jul-Aug, so beating it requires more than knowing the calendar.
    Fitted only on training years.
    """
    y = y_train.dropna()
    tr_doy = y.index.dayofyear.to_numpy()
    out = np.zeros((len(issue_dates), len(CLASSES)))
    for i, d in enumerate(issue_dates.dayofyear.to_numpy()):
        dist = np.minimum(np.abs(tr_doy - d), 365 - np.abs(tr_doy - d))
        sel = y[dist <= halfwindow]
        if len(sel) == 0:
            sel = y
        for j, c in enumerate(CLASSES):
            out[i, j] = (sel == c).mean()
    out = out / out.sum(axis=1, keepdims=True)
    return pd.DataFrame(out, index=issue_dates, columns=CLASSES)


def persistence_proba(
    labels_now: pd.Series, issue_dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """Hard persistence: the regime observed at t is asserted for t+L."""
    out = pd.DataFrame(0.0, index=issue_dates, columns=CLASSES)
    for t in issue_dates:
        if t in labels_now.index:
            out.loc[t, labels_now.loc[t]] = 1.0
        else:
            out.loc[t, :] = 1.0 / len(CLASSES)
    return out


def logistic_proba(
    X_tr: pd.DataFrame, y_tr: pd.Series, X_te: pd.DataFrame
) -> pd.DataFrame:
    """Regularised multinomial logistic reference model -- a DIAGNOSTIC, not the design.

    Stage 1 is specified as gradient boosting (CLAUDE.md Rule 3, DISCUSSION D-B)
    and that is not being revisited here. This exists only to separate two very
    different failure modes if the gate fails:

      GBM fails AND logistic fails  -> the predictors carry no usable signal
      GBM fails BUT logistic works  -> ~1.7k samples is too few for the GBM,
                                       and the problem is capacity, not signal

    Without this, a failed gate is uninterpretable.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    m = make_pipeline(
        StandardScaler(),
        # sklearn >=1.7 dropped `multi_class`; multinomial is the default for
        # lbfgs, so the behaviour is unchanged.
        LogisticRegression(max_iter=2000, C=0.1),
    )
    ok = y_tr.notna() & X_tr.notna().all(axis=1)
    m.fit(X_tr[ok].values, y_tr[ok].values)
    p = m.predict_proba(X_te.values)
    return pd.DataFrame(p, index=X_te.index, columns=list(m.classes_))[CLASSES]


@dataclass
class LeadResult:
    lead_days: int
    n_samples: int
    n_years: int
    event_days: dict[str, int]
    target_spells: dict[str, int]
    bs_model: float
    bs_climatology: float
    bs_persistence: float
    bs_seasonal_only: float
    bs_logistic: float
    bss_vs_climatology: float
    bss_vs_persistence: float
    bss_seasonal_only_vs_clim: float
    bss_logistic_vs_clim: float
    bss_per_class: dict[str, float]
    bss_ci: tuple[float, float]
    per_year: pd.DataFrame = field(repr=False, default=None)

    def beats_climatology(self) -> bool:
        """Strict: positive skill AND a bootstrap interval that excludes zero."""
        return self.bss_vs_climatology > 0 and self.bss_ci[0] > 0


def _bootstrap_bss_ci(
    per_sample_model: pd.Series,
    per_sample_ref: pd.Series,
    years: np.ndarray,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Block bootstrap over YEARS -- the only plausibly independent unit here."""
    rng = np.random.default_rng(seed)
    uy = np.unique(years)
    by_year = {
        y: (per_sample_model[years == y].to_numpy(), per_sample_ref[years == y].to_numpy())
        for y in uy
    }
    out = []
    for _ in range(n_boot):
        pick = rng.choice(uy, size=len(uy), replace=True)
        m = np.concatenate([by_year[y][0] for y in pick])
        r = np.concatenate([by_year[y][1] for y in pick])
        if r.mean() <= 0:
            continue
        out.append(1.0 - m.mean() / r.mean())
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def leave_one_year_out(
    X: pd.DataFrame,
    labels: pd.Series,
    lead_days: int,
    target_window_days: int = 7,
    n_boot: int = 2000,
    seasonal_cols: tuple[str, ...] = ("doy_sin", "doy_cos"),
    verbose: bool = True,
) -> LeadResult:
    """Run the full LOYO backtest for one lead time."""
    y_future = make_future_target(labels, lead_days, target_window_days)
    common = X.index.intersection(y_future.dropna().index)
    X, y_future = X.loc[common], y_future.loc[common]
    labels_now = labels.loc[labels.index.intersection(common)]

    years = np.array(sorted(set(X.index.year)))
    preds, clim, pers, seas, logit, truth = [], [], [], [], [], []

    for y in years:
        te = X.index.year == y
        tr = ~te
        if te.sum() == 0 or tr.sum() == 0:
            continue

        fc = RegimeForecaster(lead_days=lead_days, target_window_days=target_window_days)
        fc.fit(X[tr], y_future[tr])
        preds.append(fc.forecast_proba(X[te]).proba)

        sc = RegimeForecaster(lead_days=lead_days, target_window_days=target_window_days)
        sc.fit(X.loc[tr, list(seasonal_cols)], y_future[tr], tune=False)
        seas.append(sc.forecast_proba(X.loc[te, list(seasonal_cols)]).proba)

        logit.append(logistic_proba(X[tr], y_future[tr], X[te]))
        clim.append(climatology_proba(y_future[tr], X.index[te]))
        pers.append(persistence_proba(labels_now, X.index[te]))
        truth.append(y_future[te])

    P = pd.concat(preds).sort_index()
    C = pd.concat(clim).sort_index()
    R = pd.concat(pers).sort_index()
    S = pd.concat(seas).sort_index()
    L = pd.concat(logit).sort_index()
    T = pd.concat(truth).sort_index()

    bs_m, bs_c = multiclass_brier(P, T), multiclass_brier(C, T)
    bs_p, bs_s = multiclass_brier(R, T), multiclass_brier(S, T)
    bs_l = multiclass_brier(L, T)

    sm, sc_ = brier_by_sample(P, T), brier_by_sample(C, T)
    idx = sm.index.intersection(sc_.index)
    ci = _bootstrap_bss_ci(sm.loc[idx], sc_.loc[idx], idx.year.to_numpy(), n_boot=n_boot)

    per_year = pd.DataFrame(
        {
            "model": sm.groupby(sm.index.year).mean(),
            "climatology": sc_.groupby(sc_.index.year).mean(),
        }
    )
    per_year["bss"] = 1 - per_year["model"] / per_year["climatology"]

    # Distinct spells in the TARGET series -- the event count that must be stated.
    spells = {}
    for cls in ("active", "break"):
        runs, prev = 0, None
        for v in T.values:
            if v == cls and prev != cls:
                runs += 1
            prev = v
        spells[cls] = runs

    res = LeadResult(
        lead_days=lead_days,
        n_samples=len(T),
        n_years=len(years),
        event_days={c: int((T == c).sum()) for c in CLASSES},
        target_spells=spells,
        bs_model=bs_m,
        bs_climatology=bs_c,
        bs_persistence=bs_p,
        bs_seasonal_only=bs_s,
        bs_logistic=bs_l,
        bss_vs_climatology=1 - bs_m / bs_c,
        bss_vs_persistence=1 - bs_m / bs_p,
        bss_seasonal_only_vs_clim=1 - bs_s / bs_c,
        bss_logistic_vs_clim=1 - bs_l / bs_c,
        bss_per_class={
            c: 1 - binary_brier(P, T, c) / binary_brier(C, T, c) for c in CLASSES
        },
        bss_ci=ci,
        per_year=per_year,
    )
    if verbose:
        print(format_lead(res), flush=True)
    return res


def format_lead(r: LeadResult) -> str:
    lead_wk = r.lead_days / 7
    return (
        f"\n--- LEAD {lead_wk:.0f} WEEK ({r.lead_days} days) ---\n"
        f"  samples {r.n_samples} over {r.n_years} held-out years\n"
        f"  target regime days: {r.event_days}\n"
        f"  target spells:      {r.target_spells}\n"
        f"  Brier  model={r.bs_model:.4f}  climatology={r.bs_climatology:.4f}  "
        f"persistence={r.bs_persistence:.4f}  seasonal-only={r.bs_seasonal_only:.4f}  "
        f"logistic={r.bs_logistic:.4f}\n"
        f"  BSS vs climatology  = {r.bss_vs_climatology:+.4f}  "
        f"[95% block-bootstrap CI {r.bss_ci[0]:+.4f}, {r.bss_ci[1]:+.4f}]\n"
        f"  BSS vs persistence  = {r.bss_vs_persistence:+.4f}\n"
        f"  seasonal-only BSS   = {r.bss_seasonal_only_vs_clim:+.4f}  "
        f"(collapse test: full model must beat this)\n"
        f"  logistic diag BSS   = {r.bss_logistic_vs_clim:+.4f}  "
        f"(signal-vs-capacity diagnostic)\n"
        f"  per-class BSS       = "
        + "  ".join(f"{c}={v:+.4f}" for c, v in r.bss_per_class.items())
        + "\n"
        f"  beats climatology (skill>0 and CI excludes 0): "
        f"{'YES' if r.beats_climatology() else 'NO'}"
    )

"""Active / break / transition regime labels, Rajeevan-style.

Definition (verified 2026-09-07 against the published description, not recalled):
  Rajeevan, M., Gadgil, S. & Bhate, J. (2010), "Active and break spells of the
  Indian summer monsoon", J. Earth Syst. Sci. 119:229-247.

  - Peak monsoon months JULY and AUGUST
  - Monsoon core zone ~ 18-28N, 65-88E
  - Normalised (standardised) anomaly of MCZ-averaged daily rainfall
  - ACTIVE when the normalised anomaly exceeds +1.0 for >= 3 CONSECUTIVE days
  - BREAK  when it falls below   -1.0 for >= 3 CONSECUTIVE days
  - Everything else is neither -- called TRANSITION here to match ARCHITECTURE.md

Two implementation choices that are disclosed rather than buried:

1. SMOOTHED DAILY CLIMATOLOGY. A raw per-calendar-day mean/SD from 20 years is
   estimated from n=20 and is far too noisy to threshold at +/-1 SD. Values are
   pooled over a centred +/-7 day window across all years, giving effective
   n ~ 300 per calendar day. This is a choice, not a given; `halfwindow` exposes it.

2. LABELS ARE DEFINED ONCE FROM THE FULL RECORD. Active/break spells are an
   observational description of what happened, which is how the literature
   treats them. That does mean year Y contributes ~1/20 of the climatology used
   to label year Y. `label_stability_check()` quantifies that leakage by
   relabelling leave-one-year-out and counting days that change; the count is
   reported rather than assumed negligible (VERIFICATION.md section 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ACTIVE, BREAK, TRANSITION = "active", "break", "transition"
CLASSES = [ACTIVE, BREAK, TRANSITION]

RAJEEVAN_MONTHS = (7, 8)  # July-August, as published
RAJEEVAN_THRESHOLD = 1.0
RAJEEVAN_MIN_RUN = 3


@dataclass(frozen=True)
class RegimeLabels:
    labels: pd.Series  # index: DatetimeIndex, values in CLASSES
    z: pd.Series  # standardised MCZ rainfall anomaly
    months: tuple[int, int]
    threshold: float
    min_run: int
    halfwindow: int

    def spell_counts(self) -> dict[str, int]:
        """Number of distinct SPELLS (not days) per class -- the event count
        VERIFICATION.md requires to be stated with any score."""
        out = {}
        for cls in (ACTIVE, BREAK):
            runs, prev = 0, None
            for date, v in self.labels.items():
                if v == cls and prev != cls:
                    runs += 1
                prev = v
            out[cls] = runs
        return out

    def describe(self) -> str:
        n = self.labels.value_counts()
        sp = self.spell_counts()
        return (
            f"Rajeevan labels | months {self.months} | +/-{self.threshold} SD "
            f"sustained >={self.min_run}d | clim smoothing +/-{self.halfwindow}d\n"
            f"  days:   active={n.get(ACTIVE,0)}  break={n.get(BREAK,0)}  "
            f"transition={n.get(TRANSITION,0)}  total={len(self.labels)}\n"
            f"  spells: active={sp[ACTIVE]}  break={sp[BREAK]}"
        )


def _daily_climatology(
    rain: pd.Series, halfwindow: int, exclude_year: int | None = None
) -> tuple[pd.Series, pd.Series]:
    """Smoothed per-calendar-day mean and SD, pooled over a +/-halfwindow window.

    Returns two Series indexed by day-of-year (1..366).
    """
    src = rain if exclude_year is None else rain[rain.index.year != exclude_year]
    doy = src.index.dayofyear.values
    vals = src.values

    mu = np.full(367, np.nan)
    sd = np.full(367, np.nan)
    for d in range(1, 367):
        # circular distance in day-of-year space
        dist = np.minimum(np.abs(doy - d), 365 - np.abs(doy - d))
        sel = vals[dist <= halfwindow]
        sel = sel[~np.isnan(sel)]
        if len(sel) >= 10:
            mu[d] = sel.mean()
            sd[d] = sel.std(ddof=1)
    return pd.Series(mu), pd.Series(sd)


def _runs_at_least(mask: pd.Series, min_run: int) -> pd.Series:
    """True only where `mask` is part of a run of >= min_run consecutive True
    values. Runs are broken by calendar gaps, not just by False."""
    out = pd.Series(False, index=mask.index)
    start = None
    prev_date = None
    for i, (date, v) in enumerate(mask.items()):
        contiguous = prev_date is not None and (date - prev_date).days == 1
        if v and (start is not None) and contiguous:
            pass
        elif v:
            start = i
        else:
            start = None
        if not v:
            prev_date = date
            continue
        if start is not None and (i - start + 1) >= min_run:
            out.iloc[start : i + 1] = True
        prev_date = date
    return out


def build_labels(
    rain: pd.Series,
    months: tuple[int, int] = RAJEEVAN_MONTHS,
    threshold: float = RAJEEVAN_THRESHOLD,
    min_run: int = RAJEEVAN_MIN_RUN,
    halfwindow: int = 7,
    exclude_year: int | None = None,
) -> RegimeLabels:
    """Apply the Rajeevan criterion to an MCZ-mean daily rainfall series."""
    mu, sd = _daily_climatology(rain, halfwindow, exclude_year=exclude_year)
    doy = rain.index.dayofyear
    z = (rain.values - mu.reindex(doy).values) / sd.reindex(doy).values
    z = pd.Series(z, index=rain.index, name="z")

    in_season = (rain.index.month >= months[0]) & (rain.index.month <= months[1])
    zs = z[in_season]

    active = _runs_at_least(zs > threshold, min_run)
    brk = _runs_at_least(zs < -threshold, min_run)

    labels = pd.Series(TRANSITION, index=zs.index, name="regime")
    labels[active.values] = ACTIVE
    labels[brk.values] = BREAK

    return RegimeLabels(labels, zs, months, threshold, min_run, halfwindow)


def label_stability_check(rain: pd.Series, years: range, **kw) -> pd.DataFrame:
    """Quantify how much the full-record climatology leaks into the labels.

    For each year Y, relabel using a climatology that excludes Y and count how
    many of Y's days change label. Reported, not assumed negligible.
    """
    base = build_labels(rain, **kw).labels
    rows = []
    for y in years:
        alt = build_labels(rain, exclude_year=y, **kw).labels
        m = base.index.year == y
        b, a = base[m], alt[alt.index.year == y]
        common = b.index.intersection(a.index)
        changed = int((b.loc[common] != a.loc[common]).sum())
        rows.append({"year": y, "days": len(common), "changed": changed})
    return pd.DataFrame(rows)

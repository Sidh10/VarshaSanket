"""Phase 1R first check: does the IMD trough-position signal track observed regime?

WHAT THIS IS -- AND EXPLICITLY IS NOT
-------------------------------------
This is **not** the D-14 backtest and must not be presented as one. D-14 was
leave-one-year-out across 20 years with ~40 break spells, climatology and
persistence baselines, and block-bootstrapped intervals. This is a far smaller
association check:

  * The predictor (IMD bulletins) only exists from mid-2021.
  * imdlib rejects 2026 (partial year, "mismatch in size of data-length"), so
    the joinable range is **2021-2025 -- five monsoon seasons**.
  * Only ~18% of week-sections carry a usable directional trough position.

So the honest question here is narrow: *when IMD does state a trough direction
for a specific forecast week, does that direction correspond to the observed
Rajeevan regime in that week, more often than the base rate?* Nothing more.

Every number below is reported with its N. A result on this sample cannot
support a skill claim; it can only justify (or not justify) spending the next
build cycle on a Stage 2 interface.

THE AUTHORED STEP
-----------------
`trough.break_favourable()` maps position -> break-favourable. IMD supplies the
mechanism (glossary: trough north / at the foothills -> drastic rainfall
reduction over the core zone); IMD does NOT label these bulletins. That mapping
is ours and is the first thing a reviewer should attack.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import BREAK, build_labels
from src.features.trough import break_favourable, extract

JOIN_YEARS = (2021, 2025)     # bulletins exist from mid-2021; imdlib rejects 2026
CLIM_YEARS = (2000, 2025)     # long record for a stable daily climatology


@dataclass
class WeekOutcome:
    date: pd.Timestamp
    week: int
    position: str
    signal: float
    lead_days: int
    n_days: int
    break_frac: float
    break_dominant: bool


def build_join(
    texts: dict[str, str],
    labels: pd.Series,
    min_days: int = 4,
) -> pd.DataFrame:
    """Join each usable trough statement to the observed regime in its week.

    Week 1 of a bulletin issued on D covers D..D+6; week 2 covers D+7..D+13.
    Windows with fewer than `min_days` labelled days (season edges) are dropped
    rather than scored on a partial window.
    """
    tr = extract(texts)
    rows: list[WeekOutcome] = []
    for _, r in tr.iterrows():
        sig = break_favourable(r["position"])
        if sig is None:
            continue
        d = r["date"]
        if not (JOIN_YEARS[0] <= d.year <= JOIN_YEARS[1]):
            continue
        lead = 0 if r["week"] == 1 else 7
        lo = d + pd.Timedelta(days=lead)
        hi = lo + pd.Timedelta(days=7)
        win = labels[(labels.index >= lo) & (labels.index < hi)]
        if len(win) < min_days:
            continue
        bf = float((win == BREAK).mean())
        rows.append(
            WeekOutcome(d, int(r["week"]), r["position"], float(sig), lead,
                        len(win), bf, bf >= 0.5)
        )
    return pd.DataFrame([r.__dict__ for r in rows])


def _fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p. Used instead of a normal approximation because
    the cell counts here are single digits."""
    from math import comb

    n = a + b + c + d
    row1, col1 = a + b, a + c
    obs = comb(row1, a) * comb(n - row1, c) / comb(n, col1)
    p = 0.0
    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    for k in range(lo, hi + 1):
        pk = comb(row1, k) * comb(n - row1, col1 - k) / comb(n, col1)
        if pk <= obs * (1 + 1e-9):
            p += pk
    return min(1.0, p)


def summarise(df: pd.DataFrame, label: str) -> str:
    """Contingency + base rate + Brier, every figure carrying its N."""
    if df.empty:
        return f"[{label}] no usable statements -- N=0, nothing to report."
    n = len(df)
    base = float(df["break_dominant"].mean())
    a = int(((df.signal == 1.0) & df.break_dominant).sum())     # signal break, obs break
    b = int(((df.signal == 1.0) & ~df.break_dominant).sum())
    c = int(((df.signal == 0.0) & df.break_dominant).sum())
    d = int(((df.signal == 0.0) & ~df.break_dominant).sum())

    p_break_given_sig = a / (a + b) if (a + b) else float("nan")
    p_break_given_not = c / (c + d) if (c + d) else float("nan")
    bs_model = float(((df.signal - df.break_dominant.astype(float)) ** 2).mean())
    bs_clim = float(((base - df.break_dominant.astype(float)) ** 2).mean())
    bss = 1 - bs_model / bs_clim if bs_clim > 0 else float("nan")
    pval = _fisher_exact_2x2(a, b, c, d) if n else float("nan")

    return (
        f"[{label}]  N = {n} week-statements\n"
        f"  observed break-dominant windows: {int(df.break_dominant.sum())}/{n} "
        f"(base rate {base:.2f})\n"
        f"  contingency        obs=break  obs=not\n"
        f"    signal=break        {a:>5}    {b:>5}\n"
        f"    signal=not-break    {c:>5}    {d:>5}\n"
        f"  P(break | trough north/foothills) = {p_break_given_sig:.2f}  (n={a+b})\n"
        f"  P(break | trough south/near)      = {p_break_given_not:.2f}  (n={c+d})\n"
        f"  Brier: signal={bs_model:.4f}  climatology={bs_clim:.4f}  BSS={bss:+.4f}\n"
        f"  Fisher exact two-sided p = {pval:.3f}"
    )


def loo_calibrated_brier(df: pd.DataFrame) -> tuple[float, float, float]:
    """Leave-one-YEAR-out calibrated Brier vs climatology.

    The raw signal is hard 0/1, which Brier punishes even when the association is
    strong -- the same trap flagged for hard persistence in D-14. The fair
    question is whether a *calibrated* version of the signal beats climatology.

    Folds are at the SEASON level, not the point level. Trough position and the
    observed regime both persist across the consecutive weekly bulletins of one
    spell, so week-statements from the same season are correlated in both the
    predictor and the outcome. Point-level leave-one-out would let the
    calibration map for a held-out point be fitted on its own season's other
    points -- leakage that flatters the score. Holding out a whole season
    removes that. (An earlier version of this function did it point-level;
    see DISCUSSION D-16 for the before/after -- the year-level number was
    actually higher, but the point-level version was still wrong to use.)

    With 5 seasons and 4 break events this is a very small, fragile estimate --
    one fold (2024) contains zero break events. Read it as "not inconsistent
    with real skill", never as a skill figure.
    """
    y = df["break_dominant"].to_numpy(dtype=float)
    s = df["signal"].to_numpy(dtype=float)
    yr = df["date"].dt.year.to_numpy()
    pm, pc = np.zeros(len(y)), np.zeros(len(y))
    for year in np.unique(yr):
        te = yr == year
        tr = ~te
        if not tr.any():
            continue
        pc[te] = y[tr].mean()
        for cls in (0.0, 1.0):
            sel = te & (s == cls)
            grp = tr & (s == cls)
            pm[sel] = y[grp].mean() if grp.any() else y[tr].mean()
    bm, bc = float(((pm - y) ** 2).mean()), float(((pc - y) ** 2).mean())
    return bm, bc, (1 - bm / bc if bc > 0 else float("nan"))


def event_coverage(texts: dict[str, str], labels: pd.Series) -> str:
    """Of the observed break-dominant windows in range, how many did a bulletin
    actually give us a usable trough statement for? Recall of the *pipeline*,
    not of the classifier -- a signal we cannot read is a signal we do not have."""
    tr = extract(texts)
    tr = tr[(tr["date"].dt.year >= JOIN_YEARS[0]) & (tr["date"].dt.year <= JOIN_YEARS[1])]
    total = usable = 0
    for _, r in tr.iterrows():
        lead = 0 if r["week"] == 1 else 7
        lo = r["date"] + pd.Timedelta(days=lead)
        win = labels[(labels.index >= lo) & (labels.index < lo + pd.Timedelta(days=7))]
        if len(win) < 4:
            continue
        if (win == BREAK).mean() >= 0.5:
            total += 1
            if break_favourable(r["position"]) is not None:
                usable += 1
    return (f"break-dominant windows in {JOIN_YEARS[0]}-{JOIN_YEARS[1]} covered by a "
            f"bulletin week-section: {total}; of those with a usable trough "
            f"position: {usable} ({100*usable/total:.0f}%)" if total else
            "no break-dominant windows in range")


def main() -> None:
    print("=" * 78)
    print("PHASE 1R CHECK -- IMD trough position vs observed Rajeevan regime")
    print("NOT the D-14 backtest. Association check on 5 seasons. N stated throughout.")
    print("=" * 78)

    from src.data.imd_bulletins import load_jjas_bulletin_texts
    from src.features.mcz import coverage_for_text, region_proxy_error
    from src.features.trough import coverage_report

    texts = load_jjas_bulletin_texts((2021, 2026))
    tr = extract(texts)
    print("\n--- trough extraction ---")
    print(coverage_report(tr))

    print("\n--- MCZ reconciliation ---")
    print(region_proxy_error())
    cov = [coverage_for_text(t).frac_area_mentioned for t in texts.values()]
    print(f"  per-bulletin MCZ area-weighted coverage: median {np.median(cov):.2f} "
          f"(min {min(cov):.2f}, max {max(cov):.2f}, n={len(cov)})")

    print("\n--- labels (Rajeevan, JJAS) ---")
    rain = load_mcz_rainfall(*CLIM_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    print(f"  climatology from {CLIM_YEARS[0]}-{CLIM_YEARS[1]}; "
          f"labels joined over {JOIN_YEARS[0]}-{JOIN_YEARS[1]}")
    print("  " + lab.describe().replace("\n", "\n  "))

    df = build_join(texts, lab.labels)
    if df.empty:
        print("\nNo joinable statements. Nothing to report.")
        return

    print("\n--- position distribution in the joined sample ---")
    print("  " + df["position"].value_counts().to_string().replace("\n", "\n  "))

    print("\n" + "-" * 78)
    print(summarise(df, "ALL leads (week 1 + week 2 pooled)"))
    for wk, lead in ((1, "0-6 d"), (2, "7-13 d")):
        sub = df[df.week == wk]
        print("\n" + summarise(sub, f"week {wk} (lead {lead})"))

    print("\n" + "-" * 78)
    print("CALIBRATION CHECK (leave-one-out; raw signal is hard 0/1)")
    for name, sub in (("all", df), ("week 2", df[df.week == 2])):
        if len(sub) < 6:
            print(f"  [{name}] N={len(sub)} -- too few to calibrate, skipped")
            continue
        bm, bc, bss = loo_calibrated_brier(sub)
        print(f"  [{name}] N={len(sub)}  LOO-calibrated Brier={bm:.4f}  "
              f"climatology={bc:.4f}  BSS={bss:+.4f}")

    print("\n" + "-" * 78)
    print("PIPELINE COVERAGE OF EVENTS")
    print("  " + event_coverage(texts, lab.labels))

    print("\n" + "=" * 78)
    print("Sample size is the binding constraint, not the statistic. Read the Ns.")


if __name__ == "__main__":
    main()

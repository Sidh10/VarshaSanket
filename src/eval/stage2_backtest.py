"""Stage 2 validation. THE ONLY PLACE STAGE 2 ACCURACY METRICS ARE COMPUTED.

THE QUESTION
------------
Does ENSO/IOD-weighted analog selection produce a measurably better-calibrated
distribution of SEASONAL rainfall outcome than unweighted climatology? If not,
Stage 2 is decoration on top of Stage 1 and should be said to be.

PROTOCOL (mirrors D-14 deliberately, so the two are comparable)
---------------------------------------------------------------
  * Leave-one-year-out across all 20 years -- never a single split.
  * The held-out year is excluded from: the analog pool, the index
    standardisation, the tercile boundaries, and the climatology baseline.
  * Scored against unweighted climatology, the same baseline D-14 used.
  * Uncertainty block-bootstrapped over YEARS.
  * Hyper-parameters fixed a priori; the sensitivity grid is printed in full so
    the spread is visible rather than the best cell being quoted (Michaelsen).

THE SAMPLE, STATED UP FRONT
---------------------------
**N = 20 seasonal outcomes.** Not 20 years of daily data -- 20 events, roughly
7 dry / 6 normal / 7 wet. Every figure below rests on that. A seasonal-scale
question simply cannot have a large sample from a 20-year record, and no
statistic here can be quoted as though it did.

METRIC
------
Ranked Probability Score. Terciles are ORDERED (dry < normal < wet), so RPS is
the right metric -- it penalises predicting "wet" for a dry year more than
predicting "normal" for a dry year, which plain Brier does not. Brier is
reported alongside for continuity with D-14.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.seasonal_state import TERCILES, build_seasonal_table, tercile_labels
from src.models.analog_downscaler import AnalogDownscaler


def rps(prob: dict[str, float], observed: str) -> float:
    """Ranked probability score for ordered terciles, normalised to [0, 1]."""
    p = np.array([prob[c] for c in TERCILES])
    o = np.array([1.0 if c == observed else 0.0 for c in TERCILES])
    return float(((np.cumsum(p) - np.cumsum(o))[:-1] ** 2).sum() / (len(TERCILES) - 1))


def brier(prob: dict[str, float], observed: str) -> float:
    p = np.array([prob[c] for c in TERCILES])
    o = np.array([1.0 if c == observed else 0.0 for c in TERCILES])
    return float(((p - o) ** 2).sum())


def _bootstrap_skill_ci(model: np.ndarray, ref: np.ndarray, n_boot=2000, seed=0):
    """Block bootstrap over years -- the independent unit is the season."""
    rng = np.random.default_rng(seed)
    n = len(model)
    out = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        r = ref[i].mean()
        if r > 0:
            out.append(1 - model[i].mean() / r)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def run_loyo(
    table: pd.DataFrame,
    state_window: str,
    bandwidth: float,
    recency_tau: float,
    use_recency: bool = True,
) -> dict:
    """Leave-one-year-out over every year in `table`."""
    years = table.index.to_numpy()
    rows = []
    for y in years:
        # Terciles WITHOUT the held-out year -- it does not help define the
        # category it is scored against.
        labels = tercile_labels(table.rain_total, exclude_year=int(y))
        obs = labels[y]

        dsc = AnalogDownscaler(state_window, bandwidth, recency_tau, use_recency).fit(table)
        out = dsc.downscale(int(y), labels)

        # Climatology baseline: unweighted tercile frequency over the pool only.
        pool = years[years != y]
        clim = {c: float((labels[pool] == c).mean()) for c in TERCILES}
        s = sum(clim.values()) or 1.0
        clim = {c: v / s for c, v in clim.items()}

        rows.append(
            {
                "year": int(y),
                "observed": obs,
                "rps_model": rps(out.outcome_probabilities, obs),
                "rps_clim": rps(clim, obs),
                "brier_model": brier(out.outcome_probabilities, obs),
                "brier_clim": brier(clim, obs),
                "effective_n": out.effective_n,
                "p_obs_model": out.outcome_probabilities[obs],
                "p_obs_clim": clim[obs],
            }
        )
    df = pd.DataFrame(rows)
    rm, rc = df.rps_model.to_numpy(), df.rps_clim.to_numpy()
    lo, hi = _bootstrap_skill_ci(rm, rc)
    return {
        "frame": df,
        "n": len(df),
        "rpss": 1 - rm.mean() / rc.mean(),
        "rpss_ci": (lo, hi),
        "bss": 1 - df.brier_model.mean() / df.brier_clim.mean(),
        "neff_median": float(df.effective_n.median()),
        "neff_min": float(df.effective_n.min()),
    }


def main() -> None:
    print("=" * 78)
    print("STAGE 2 VALIDATION -- analog downscaler vs unweighted climatology")
    print("LOYO over 20 seasons. N = 20 EVENTS. Read that before any number below.")
    print("=" * 78)

    st = build_seasonal_table((2000, 2019))
    print("\n" + st.describe())
    t = st.frame

    print("\nseasonal predictor / outcome correlations (n=20):")
    for c in ("nino34_jjas", "dmi_jjas", "nino34_mam", "dmi_mam"):
        print(f"  {c:14s} r vs seasonal rainfall = "
              f"{np.corrcoef(t[c], t.rain_total)[0,1]:+.3f}")

    results = {}
    for win, tag in (("jjas", "CONCURRENT (diagnostic -- not knowable pre-season)"),
                     ("mam", "PRE-SEASON (operationally usable)")):
        r = run_loyo(t, win, 1.0, 15.0)
        results[win] = r
        print("\n" + "-" * 78)
        print(f"[{win.upper()}] {tag}")
        print("-" * 78)
        print(f"  N = {r['n']} seasons")
        print(f"  RPSS vs climatology = {r['rpss']:+.4f}   "
              f"95% CI [{r['rpss_ci'][0]:+.4f}, {r['rpss_ci'][1]:+.4f}]")
        print(f"  BSS  vs climatology = {r['bss']:+.4f}")
        print(f"  effective ensemble size: median {r['neff_median']:.1f}, "
              f"min {r['neff_min']:.1f}  (Phase 2 gate wants >= ~10)")

    print("\n" + "-" * 78)
    print("SENSITIVITY GRID -- printed in full; the best cell is NOT the result")
    print("-" * 78)
    print(f"{'window':8s} {'bw':>5} {'tau':>6} {'recency':>8} {'RPSS':>9} {'N_eff med':>10}")
    for win in ("jjas", "mam"):
        for bw in (0.5, 1.0, 2.0):
            for tau, rec in ((15.0, True), (1e9, False)):
                r = run_loyo(t, win, bw, tau, rec)
                print(f"{win:8s} {bw:>5.1f} {('off' if not rec else f'{tau:.0f}'):>6} "
                      f"{str(rec):>8} {r['rpss']:>+9.4f} {r['neff_median']:>10.1f}")

    print("\n" + "=" * 78)
    print("PER-YEAR DETAIL (concurrent JJAS window)")
    print("=" * 78)
    d = results["jjas"]["frame"]
    print(d[["year", "observed", "p_obs_model", "p_obs_clim",
             "rps_model", "rps_clim", "effective_n"]].round(3).to_string(index=False))

    print("\n" + "=" * 78)
    j, m = results["jjas"], results["mam"]
    gate_j = j["rpss"] > 0 and j["rpss_ci"][0] > 0
    gate_m = m["rpss"] > 0 and m["rpss_ci"][0] > 0
    print(f"CONCURRENT (diagnostic)  RPSS {j['rpss']:+.4f}  CI excludes 0: {gate_j}")
    print(f"PRE-SEASON (operational) RPSS {m['rpss']:+.4f}  CI excludes 0: {gate_m}")
    print(f"\nEffective-N gate (>= ~10): jjas median {j['neff_median']:.1f}, "
          f"mam median {m['neff_median']:.1f}")
    print("\nThe operational number is the one that matters for a deployed system.")


if __name__ == "__main__":
    main()

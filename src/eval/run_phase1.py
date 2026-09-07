"""Phase 1 gate run: build the Regime Forecaster and validate it IN ISOLATION.

TASKS.md Phase 1 gate:
    "Stage 1 beats climatological regime frequency at >= 2 week lead.
     If not, stop and reassess -- don't paper over it with downstream complexity."

Nothing downstream (Stage 2 analog downscaler, Stage 3 calibration, Stage 4
decision engine) may be built until this run reports the gate CLEARED.

Usage:  python -m src.eval.run_phase1
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from src.data.imd_rainfall import load_mcz_rainfall
from src.data.indices import load_indices
from src.data.iwb_fields import load_aux_fields
from src.eval.backtest import leave_one_year_out
from src.features.labels import build_labels, label_stability_check
from src.features.trajectory import PUBLICATION_LAG_DAYS, build_features

YEARS = (2000, 2019)
LEADS_DAYS = [7, 14, 21, 28]
TARGET_WINDOW = 7
ARTIFACTS = "artifacts"

# Two season definitions are run, and BOTH are reported. This is a disclosed
# choice, not a silently-picked convenience:
#
#   JJAS (6,9)  -- PRIMARY. Needed for the leads to be comparable to each other.
#                  With strict Jul-Aug, a 4-week lead + 7-day target window only
#                  leaves issue dates from 1-27 July (~27/year, all in July),
#                  while a 1-week lead keeps ~48/year. Scoring those two against
#                  each other would compare different seasons, not different leads.
#   Jul-Aug (7,8) -- SENSITIVITY. The literal Rajeevan et al. (2010) window.
#                  Reported so the deviation is visible and checkable.
#
# If the two disagree about the gate, that disagreement is the finding and gets
# reported as such -- the more favourable one is not adopted as "the" answer.
SEASONS = {
    "JJAS (primary)": (6, 9),
    "Jul-Aug (strict Rajeevan, sensitivity)": (7, 8),
}


def main() -> None:
    os.makedirs(ARTIFACTS, exist_ok=True)
    print("=" * 78)
    print("VarshaSanket -- STAGE 1 REGIME FORECASTER -- Phase 1 isolation validation")
    print("=" * 78)

    # ---------------------------------------------------------------- ground truth
    print("\n[1/5] IMD gridded rainfall -> monsoon core zone daily mean")
    rain = load_mcz_rainfall(*YEARS)
    print("  ", rain.describe())

    # ---------------------------------------------------------------- predictors
    print("\n[2/5] Teleconnection indices (native cadences)")
    idx = load_indices()
    print(idx.describe())

    print("\n[3/5] IndiaWeatherBench auxiliary fields (coarse H500 / T850 over MCZ)")
    aux = load_aux_fields(YEARS)
    print("  ", aux.describe())

    all_results: dict[str, list] = {}
    meta: dict[str, dict] = {}

    for season_name, months in SEASONS.items():
        print("\n" + "#" * 78)
        print(f"# SEASON DEFINITION: {season_name}   months={months}")
        print("#" * 78)

        print("\n[4/5] Rajeevan active/break/transition labels")
        lab = build_labels(rain.series, months=months)
        print(lab.describe())

        stab = label_stability_check(
            rain.series, range(YEARS[0], YEARS[1] + 1), months=months
        )
        tot, chg = int(stab["days"].sum()), int(stab["changed"].sum())
        print(
            f"  label leakage check: relabelling leave-one-year-out changes "
            f"{chg}/{tot} days ({100*chg/tot:.2f}%) -- reported, not assumed negligible"
        )

        feats = build_features(idx, aux.frame, lab.labels.index)
        print("\n  ", feats.describe().replace("\n", "\n  "))
        n_missing = int(feats.X.isna().any(axis=1).sum())
        print(f"   rows dropped for incomplete predictors: {n_missing}/{len(feats.X)}")

        # ------------------------------------------------------------ validation
        print("\n[5/5] Leave-one-year-out backtest across 20 years, per lead")
        print("      baselines: day-of-year climatology + hard persistence")
        print("      NO feature selection anywhere (Michaelsen 1987: screening is")
        print("      the largest source of artificial skill).")
        print("      Capacity IS selected, but only by inner GroupKFold over the")
        print("      training years -- the held-out year is never touched.")

        results = [
            leave_one_year_out(
                feats.X, lab.labels, lead_days=lead, target_window_days=TARGET_WINDOW
            )
            for lead in LEADS_DAYS
        ]
        all_results[season_name] = results
        meta[season_name] = {
            "months": list(months),
            "label_leakage_days_changed": chg,
            "label_leakage_days_total": tot,
            "n_features": int(feats.X.shape[1]),
            "label_days": {k: int(v) for k, v in lab.labels.value_counts().items()},
            "label_spells": lab.spell_counts(),
        }

        print("\n" + "=" * 78)
        print(f"SUMMARY [{season_name}] -- BSS vs day-of-year climatology, per lead")
        print("=" * 78)
        print(
            f"{'lead':>6} {'n':>6} {'BSS vs clim':>13} {'95% CI':>22} "
            f"{'BSS vs pers':>12} {'seas-only':>11} {'logistic':>10} {'beats clim':>11}"
        )
        for r in results:
            print(
                f"{r.lead_days//7:>4}wk {r.n_samples:>6} {r.bss_vs_climatology:>+13.4f} "
                f"  [{r.bss_ci[0]:+.4f}, {r.bss_ci[1]:+.4f}] "
                f"{r.bss_vs_persistence:>+12.4f} {r.bss_seasonal_only_vs_clim:>+11.4f} "
                f"{r.bss_logistic_vs_clim:>+10.4f} "
                f"{('YES' if r.beats_climatology() else 'NO'):>11}"
            )

    # ---------------------------------------------------------------- gate verdict
    print("\n" + "=" * 78)
    print("PHASE 1 GATE (TASKS.md): 'Stage 1 beats climatological regime")
    print("frequency at >= 2 week lead. If not, stop and reassess.'")
    print("=" * 78)

    verdicts = {}
    for season_name, results in all_results.items():
        two_wk = next(r for r in results if r.lead_days == 14)
        verdicts[season_name] = two_wk.beats_climatology()
        print(f"\n  [{season_name}]")
        print(f"    2-week BSS vs climatology : {two_wk.bss_vs_climatology:+.4f}")
        print(
            f"    95% block-bootstrap CI    : "
            f"[{two_wk.bss_ci[0]:+.4f}, {two_wk.bss_ci[1]:+.4f}]  (resampled over years)"
        )
        print(f"    samples / held-out years  : {two_wk.n_samples} / {two_wk.n_years}")
        print(f"    target regime days        : {two_wk.event_days}")
        print(f"    target spells             : {two_wk.target_spells}")
        print(f"    verdict                   : {'CLEARED' if verdicts[season_name] else 'NOT CLEARED'}")

    gate = all(verdicts.values())
    print("\n" + "-" * 78)
    print(f"  OVERALL GATE: {'CLEARED' if gate else 'NOT CLEARED'}")
    if not gate:
        print(
            "\n  Per TASKS.md: STOP. Do not build Stage 2 on top of this.\n"
            "  Downstream complexity cannot recover skill Stage 1 does not have."
        )
    if len(set(verdicts.values())) > 1:
        print(
            "\n  NOTE: the two season definitions DISAGREE. That disagreement is\n"
            "  itself the finding and is reported as such -- the more favourable\n"
            "  definition is not being adopted as 'the' answer."
        )

    payload = {
        "years": YEARS,
        "target_window_days": TARGET_WINDOW,
        "publication_lags": dict(PUBLICATION_LAG_DAYS),
        "gate_2week_cleared_overall": bool(gate),
        "gate_by_season": {k: bool(v) for k, v in verdicts.items()},
        "seasons": {
            season_name: {
                **meta[season_name],
                "leads": [
                    {
                        "lead_days": r.lead_days,
                        "n_samples": r.n_samples,
                        "event_days": r.event_days,
                        "target_spells": r.target_spells,
                        "bs_model": r.bs_model,
                        "bs_climatology": r.bs_climatology,
                        "bs_persistence": r.bs_persistence,
                        "bs_seasonal_only": r.bs_seasonal_only,
                        "bs_logistic": r.bs_logistic,
                        "bss_vs_climatology": r.bss_vs_climatology,
                        "bss_vs_persistence": r.bss_vs_persistence,
                        "bss_seasonal_only_vs_clim": r.bss_seasonal_only_vs_clim,
                        "bss_logistic_vs_clim": r.bss_logistic_vs_clim,
                        "bss_per_class": r.bss_per_class,
                        "bss_ci95": list(r.bss_ci),
                    }
                    for r in results
                ],
            }
            for season_name, results in all_results.items()
        },
    }
    with open(os.path.join(ARTIFACTS, "phase1_stage1_validation.json"), "w") as f:
        json.dump(payload, f, indent=2)
    for season_name, results in all_results.items():
        tag = "jjas" if "JJAS" in season_name else "julaug"
        for r in results:
            r.per_year.to_csv(
                os.path.join(ARTIFACTS, f"phase1_{tag}_per_year_lead{r.lead_days}.csv")
            )
    print(f"\n  wrote {ARTIFACTS}/phase1_stage1_validation.json")


if __name__ == "__main__":
    main()

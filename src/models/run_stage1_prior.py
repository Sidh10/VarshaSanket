"""Exercise Stage 1 (climatological prior) + Stage 2 (analog evidence) and print
the full handoff schema.

Usage:  python -m src.models.run_stage1_prior

Stage 2 is included as EVIDENCE ONLY -- named analog years and their observed
outcomes, attached alongside Stage 1's probabilities and asserted not to alter
them. Stage 2's original probability-reweighting role was retired after D-17.

Deliberately does NOT touch Stage 4.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import build_labels
from src.models.climatological_prior import (
    REGIME_CLASSES,
    ClimatologicalPrior,
    verify_matches_backtest_baseline,
)

LABEL_YEARS = (2000, 2019)   # the validated D-14 label set
DEMO_DATES = ["2019-06-15", "2019-07-15", "2019-08-15", "2019-09-15"]


def main() -> None:
    print("=" * 78)
    print("STAGE 1 -- CLIMATOLOGICAL REGIME PRIOR  (not a forecaster)")
    print("=" * 78)

    rain = load_mcz_rainfall(*LABEL_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    print("\n[labels] " + lab.describe().replace("\n", "\n         "))

    ok = verify_matches_backtest_baseline(
        lab.labels, pd.date_range("2019-06-01", "2019-09-30")
    )
    print(f"\n[refactor check] production prior == D-14 backtest baseline: {ok}")
    if not ok:
        raise SystemExit("REFACTOR CHANGED D-14 NUMBERS -- stop and investigate")

    prior = ClimatologicalPrior().fit(lab.labels)

    # --- optional evidence block (text only, never numeric) ----------------
    try:
        from src.data.imd_bulletins import load_jjas_bulletin_texts
        from src.features.trough import advisory_evidence_for, extract

        stmts = extract(load_jjas_bulletin_texts((2021, 2026)))
    except Exception as e:  # evidence is optional by design
        stmts = None
        print(f"\n[evidence] unavailable ({type(e).__name__}) -- priors unaffected")

    print("\n" + "-" * 78)
    print("SAMPLE PRIORS")
    print("-" * 78)
    for d in DEMO_DATES:
        p = prior.prior_for(d)
        print("\n" + p.describe())

    # --- demonstrate the two outputs are structurally independent ----------
    print("\n" + "-" * 78)
    print("SEPARATION CHECK -- evidence must not alter probabilities")
    print("-" * 78)
    base = prior.prior_for("2019-07-15")
    withev = prior.prior_for(
        "2019-07-15",
        advisory_evidence="IMD bulletin: trough north of normal in week 2.",
        evidence_source="IMD ERF bulletin (synthetic, for the assertion below)",
    )
    same = base.probabilities == withev.probabilities
    print(f"  probabilities identical with and without evidence: {same}")
    assert same, "evidence leaked into the numeric block"
    print(f"  advisory_evidence present only in the second: "
          f"{base.advisory_evidence is None and withev.advisory_evidence is not None}")

    # --- real evidence coverage over the joinable range --------------------
    if stmts is not None:
        rng = pd.date_range("2021-06-01", "2025-09-30")
        rng = rng[(rng.month >= 6) & (rng.month <= 9)]
        hits = sum(1 for d in rng if advisory_evidence_for(d, stmts) is not None)
        print("\n" + "-" * 78)
        print("EVIDENCE COVERAGE (text field only -- does not affect probabilities)")
        print("-" * 78)
        print(f"  JJAS dates 2021-2025 with usable IMD trough evidence: "
              f"{hits}/{len(rng)} ({100*hits/len(rng):.0f}%)")
        # Pair the date with evidence that actually COVERS that date -- an
        # earlier version of this demo showed a date next to an unrelated
        # bulletin's evidence, which is exactly the kind of mismatch the
        # advisory must never ship.
        pair = next(
            ((d, e) for d in rng if (e := advisory_evidence_for(d, stmts))), None
        )
        if pair:
            d, (text, src) = pair
            real = prior.prior_for(d, advisory_evidence=text, evidence_source=src)
            print("\n  example populated RegimePrior (evidence genuinely covers this date):")
            print("  " + real.describe().replace("\n", "\n  "))

    # --- Stage 2: seasonal analog evidence (historical lookup, not a forecast)
    print("\n" + "-" * 78)
    print("STAGE 2 -- SEASONAL ANALOG EVIDENCE (K nearest pre-season ENSO/IOD years)")
    print("-" * 78)
    from src.features.seasonal_state import build_seasonal_table
    from src.models.climatological_prior import attach_seasonal_analog
    from src.models.seasonal_analog_evidence import build_evidence

    st = build_seasonal_table(LABEL_YEARS).frame
    agree_counts: dict[str, int] = {}
    for y in st.index:
        ev = build_evidence(st, int(y))
        agree_counts[ev.agreement] = agree_counts.get(ev.agreement, 0) + 1
    print(f"  agreement across all {len(st)} target years: {agree_counts}")

    for y in (2002, 2019):
        ev = build_evidence(st, y)
        print("\n  " + ev.describe().replace("\n", "\n  "))

    # --- separation check #2: analog evidence must not alter probabilities --
    print("\n" + "-" * 78)
    print("SEPARATION CHECK 2 -- analog evidence must not alter probabilities")
    print("-" * 78)
    p0 = prior.prior_for("2019-07-15")
    ev19 = build_evidence(st, 2019)
    p1 = attach_seasonal_analog(p0, ev19)
    checks = {
        "probabilities identical": p0.probabilities == p1.probabilities,
        "ci_lower identical": p0.ci_lower == p1.ci_lower,
        "ci_upper identical": p0.ci_upper == p1.ci_upper,
        "effective_n identical": p0.effective_n == p1.effective_n,
        "analog fields populated only on p1": (
            p0.seasonal_analog_evidence is None
            and p1.seasonal_analog_evidence is not None
        ),
        "bulletin evidence untouched by analog attach": (
            p0.advisory_evidence == p1.advisory_evidence
        ),
    }
    for k, v in checks.items():
        print(f"  {k}: {v}")
    assert all(checks.values()), "analog evidence leaked into the numeric block"

    # --- both evidence mechanisms present at once, still separate ----------
    both = attach_seasonal_analog(
        prior.prior_for(
            "2019-07-15",
            advisory_evidence="IMD bulletin: trough north of normal in week 2.",
            evidence_source="IMD ERF bulletin 2019-07-10, week 2",
        ),
        ev19,
    )
    print("\n  both mechanisms attached simultaneously:")
    print("  " + both.describe().replace("\n", "\n  "))
    assert both.probabilities == p0.probabilities, "fusion detected"

    # --- D-19: farmer-facing vs technical evidence views ------------------
    print("\n" + "-" * 78)
    print("D-19 -- farmer-facing advisory lines vs full technical view")
    print("-" * 78)
    from src.models.climatological_prior import (
        advisory_evidence_lines,
        advisory_evidence_technical_view,
    )

    # 2018 is the only 'leaning' year in the record; every other year is 'divided'.
    st18 = attach_seasonal_analog(prior.prior_for("2018-07-15"), build_evidence(st, 2018))
    st19 = both  # 2019 analog evidence = 'divided'
    for tag, pr in (("2018 (leaning)", st18), ("2019 (divided)", st19)):
        tv = advisory_evidence_technical_view(pr)
        print(f"\n  [{tag}]  agreement={tv['seasonal_analog_agreement']}  "
              f"advisory_visible={tv['seasonal_analog_advisory_visible']}")
        print(f"    technical view still carries analog years: {tv['seasonal_analog_years']}")
        print(f"    suppressed_reason: {tv['seasonal_analog_suppressed_reason']}")
        lines = advisory_evidence_lines(pr)
        print(f"    FARMER-FACING lines ({len(lines)}):")
        for ln in lines:
            print(f"      - {ln}")
        if not lines:
            print("      (none -- nothing surfaced to the farmer from evidence)")
    assert advisory_evidence_technical_view(st19)["seasonal_analog_evidence"], \
        "divided-case data must remain populated in the technical view"
    assert not any(
        st19.seasonal_analog_evidence == ln for ln in advisory_evidence_lines(st19)
    ), "divided-case analog evidence must NOT reach the farmer"
    print("\n  asserted: divided-case data retained in API, absent from farmer text.")

    # --- the schema, spelled out ------------------------------------------
    print("\n" + "=" * 78)
    print("STAGE 2 HANDOFF SCHEMA (RegimePrior)")
    print("=" * 78)
    p = prior.prior_for("2019-07-15")
    schema = {
        "target_date": str(p.target_date),
        "day_of_year": p.day_of_year,
        "probabilities": {k: round(v, 4) for k, v in p.probabilities.items()},
        "ci_lower": {k: round(v, 4) for k, v in p.ci_lower.items()},
        "ci_upper": {k: round(v, 4) for k, v in p.ci_upper.items()},
        "n_years": p.n_years,
        "n_labelled_days": p.n_labelled_days,
        "effective_n": p.effective_n,
        "source_years": list(p.source_years),
        "halfwindow_days": p.halfwindow_days,
        "method": p.method,
        "advisory_evidence": p.advisory_evidence,
        "evidence_source": p.evidence_source,
        "seasonal_analog_evidence": both.seasonal_analog_evidence,
        "seasonal_analog_years": list(both.seasonal_analog_years or ()),
        "seasonal_analog_detail": [
            {**a, "distance": round(a["distance"], 4)}
            for a in (both.seasonal_analog_detail or ())
        ],
        "seasonal_analog_effective_n": round(both.seasonal_analog_effective_n or 0, 3),
        "seasonal_analog_agreement": both.seasonal_analog_agreement,
        "seasonal_analog_advisory_visible": both.seasonal_analog_advisory_visible,
        "farmer_facing_evidence_lines": advisory_evidence_lines(both),
    }
    print(json.dumps(schema, indent=2))
    print("\nClasses:", list(REGIME_CLASSES))
    print("Numeric block   = probabilities / ci_lower / ci_upper   (climatology only)")
    print("Evidence block A = advisory_evidence / evidence_source  (IMD bulletin parsing)")
    print("Evidence block B = seasonal_analog_*                    (historical fact lookup)")
    print("Neither evidence block is numeric input; both are asserted non-fusing above.")
    print("`farmer_facing_evidence_lines` = D-19 filter: analog evidence only when")
    print("  agreement in {leaning, unanimous}; 'divided' stays in the schema, not the")
    print("  advisory. Here 2019 is 'divided', so only the bulletin line is farmer-facing.")
    print("\nStage 2 supplies EVIDENCE ONLY (probability reweighting retired, D-17).")
    print("Stage 4 is NOT started. This defines the contract and stops.")


if __name__ == "__main__":
    main()

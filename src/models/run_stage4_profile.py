"""Stage 4 per-farmer worked example. Usage: python -m src.models.run_stage4_profile

Extends the Stage 4 worked example (run_stage4_decision.py) with the per-farmer
loss-side layer from `farmer_profile.py`. Same Stage 1 prior, same date, same
regime probabilities throughout -- only the farmer's own loss inputs change.

What this demonstrates, in order:
  1. The D-C guard covers every profile path (27-combo grid + rejection tests).
  2. Stage 1's probabilities are byte-identical across every profile.
  3. An all-reference profile reproduces the base decision exactly.
  4. Two illustrative profiles, SAME date + regime probabilities, produce
     OPPOSITE recommendations, with both expected losses shown for each.
  5. An already-sown profile gets NO SOW/WAIT recommendation -- different
     action set, not modelled.
"""

from __future__ import annotations

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import build_labels
from src.features.seasonal_state import build_seasonal_table
from src.models.climatological_prior import (
    ClimatologicalPrior,
    advisory_evidence_lines,
    attach_seasonal_analog,
)
from src.models.decision_engine import CROP_DEFAULTS, decide
from src.models.farmer_profile import (
    FarmerProfile,
    GrowthStage,
    IrrigationAccess,
    RiskPreference,
    SoilType,
    SowingStatus,
    check_d19_boundary,
    check_guard_covers_profile_paths,
    check_probabilities_untouched,
    check_reference_profile_is_identity,
    decide_for_profile,
)
from src.models.seasonal_analog_evidence import build_evidence

LABEL_YEARS = (2000, 2019)
TARGET_DATE = "2018-07-15"       # the one 'leaning' analog year -- both evidence lines show
CROP_A = "soybean"
CROP_B = "cotton"

_BULLETIN_EVIDENCE = (
    "IMD Extended Range bulletin places the monsoon trough north of its normal "
    "position in week 2, which IMD's glossary associates with a break in "
    "rainfall over central India."
)
_BULLETIN_SOURCE = "IMD ERF bulletin, week 2 (cached, batch-parsed - D-15/D-16)"


# ---------------------------------------------------------------------------
# The two illustrative demo profiles. NOT real registered users -- there is no
# farmer database. Chosen to differ on every loss-side field and to land on
# opposite sides of the SOW/WAIT comparison for the SAME regime probabilities.
# ---------------------------------------------------------------------------

PROFILE_A = FarmerProfile(
    label="Demo profile A -- rainfed black-soil soybean smallholder",
    crop=CROP_A,
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.RAINFED,   # no fallback -> waiting is genuinely costly
    soil=SoilType.CLAY,                     # vertisol -> a short dry spell won't kill the stand
    risk=RiskPreference.RISK_TOLERANT,      # can absorb a reseed if it goes wrong
)

PROFILE_B = FarmerProfile(
    label="Demo profile B -- irrigated sandy-plot cotton grower",
    crop=CROP_B,
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.ASSURED,    # borewell -> a missed onset is recoverable, waiting is cheap
    soil=SoilType.SANDY,                    # fast-draining -> a just-sown bed is vulnerable
    risk=RiskPreference.RISK_AVERSE,        # a reseed would hurt -> weight it heavily
)

# Same profile fields as B, but on soybean -- to show the flip is the PROFILE,
# not the crop (B still lands on WAIT with A's crop underneath it).
PROFILE_B_ON_A_CROP = FarmerProfile(
    label="Demo profile B's situation, soybean instead of cotton",
    crop=CROP_A,
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.ASSURED,
    soil=SoilType.SANDY,
    risk=RiskPreference.RISK_AVERSE,
)

PROFILE_C = FarmerProfile(
    label="Demo profile C -- crop already sown, at germination",
    crop=CROP_A,
    sowing_status=SowingStatus.SOWN,
    irrigation=IrrigationAccess.PARTIAL,
    soil=SoilType.LOAM,
    risk=RiskPreference.NEUTRAL,
    growth_stage=GrowthStage.GERMINATION,
)


def _bar(s: str) -> None:
    print("=" * 78)
    print(s)
    print("=" * 78)


def main() -> None:
    rain = load_mcz_rainfall(*LABEL_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    prior = ClimatologicalPrior().fit(lab.labels).prior_for(
        TARGET_DATE,
        advisory_evidence=_BULLETIN_EVIDENCE,
        evidence_source=_BULLETIN_SOURCE,
    )
    st = build_seasonal_table(LABEL_YEARS).frame
    prior = attach_seasonal_analog(prior, build_evidence(st, 2018))
    base_a = CROP_DEFAULTS[CROP_A]
    base_b = CROP_DEFAULTS[CROP_B]
    base_for = {
        PROFILE_A.label: base_a,
        PROFILE_B.label: base_b,
        PROFILE_B_ON_A_CROP.label: base_a,
        PROFILE_C.label: base_a,
    }

    _bar(f"STAGE 1 PRIOR (shared by every profile -- NEVER modified)")
    print(prior.describe())
    print()
    print("  Farmer-facing evidence lines (D-19 boundary, profile-independent):")
    for line in advisory_evidence_lines(prior):
        print(f"    - {line}")
    print()

    # ---- guard + immutability checks against every new code path -----------
    #      run the grid on BOTH crops' base economics.
    check_d19_boundary()
    for c, b in (("soybean", base_a), ("cotton", base_b)):
        print(f">>> guard + immutability grid on base crop = {c}")
        check_guard_covers_profile_paths(prior, b)
        check_probabilities_untouched(prior, b)
        check_reference_profile_is_identity(prior, b)
        print()

    # ---- base cases, for reference --------------------------------------
    _bar("BASE CASES -- no profile (crop defaults)")
    for b in (base_a, base_b):
        r = decide(prior, b)
        print(f"  {b.crop:9s}  L_reseed={b.l_reseed:,.0f}  L_delay={b.l_delay:,.0f}  "
              f"alpha={b.alpha}  theta={b.theta:.3f}")
        print(f"             E[loss|SOW]={r.e_loss_sow:>10,.0f}   "
              f"E[loss|WAIT]={r.e_loss_wait:>10,.0f}   -> {r.recommendation.upper()} "
              f"(robust={r.robust})")
    base_res = decide(prior, base_a)
    print()

    # ---- the two contrasting profiles -----------------------------------
    _bar("TWO ILLUSTRATIVE PROFILES -- SAME date, SAME regime probabilities")
    print(f"  target date : {TARGET_DATE}")
    print(f"  P(active)={prior.probabilities['active']:.4f}  "
          f"P(break)={prior.probabilities['break']:.4f}  "
          f"P(transition)={prior.probabilities['transition']:.4f}   "
          f"<- identical for both profiles\n")

    decisions = {}
    for prof in (PROFILE_A, PROFILE_B):
        pd_ = decide_for_profile(prior, base_for[prof.label], prof)
        decisions[prof.label] = pd_
        d = pd_.decision
        assert d is not None
        print("-" * 78)
        print(pd_.summary())
        print()
        print("  term-by-term (both branches are expectations over the SAME distribution):")
        for c in ("active", "break", "transition"):
            ls = d.loss_sow[c]
            lw = d.loss_wait[c]
            p = d.probabilities[c]
            print(f"    {c:11s} P={p:.4f}  L_sow={ls:>10,.0f}  L_wait={lw:>10,.0f}  "
                  f"contrib_sow={p*ls:>9,.1f}  contrib_wait={p*lw:>9,.1f}")
        print(f"    {'':11s} {'':>28} {'totals':>13}  "
              f"E[SOW]={d.e_loss_sow:>9,.1f}  E[WAIT]={d.e_loss_wait:>9,.1f}")
        env = "\n".join(
            f"      {k:11s} E[sow]={v['e_sow']:>9,.1f}  E[wait]={v['e_wait']:>9,.1f}  "
            f"-> {v['recommendation'].upper()}"
            for k, v in d.envelope.items()
        )
        print(f"    sensitivity envelope (marginal CI on P(break); NOT a joint interval):")
        print(env)
        print(f"    robust across envelope: {d.robust}")
        print()

    _bar("CONTRAST")
    da = decisions[PROFILE_A.label].decision
    db = decisions[PROFILE_B.label].decision
    print(f"  {PROFILE_A.label}")
    print(f"    E[SOW]={da.e_loss_sow:,.0f}  E[WAIT]={da.e_loss_wait:,.0f}  "
          f"-> {da.recommendation.upper()}")
    print(f"  {PROFILE_B.label}")
    print(f"    E[SOW]={db.e_loss_sow:,.0f}  E[WAIT]={db.e_loss_wait:,.0f}  "
          f"-> {db.recommendation.upper()}")
    print()
    print(f"  Same P(break)={prior.probabilities['break']:.1%}. The recommendations differ")
    print(f"  because the loss inputs differ -- crop AND the profile fields:")
    ma = decisions[PROFILE_A.label].multipliers
    mb = decisions[PROFILE_B.label].multipliers
    print(f"    A: crop=soybean  L_reseed x{ma['l_reseed']:.2f}  L_delay x{ma['l_delay']:.2f}  "
          f"alpha x{ma['alpha']:.2f}   (rainfed -> waiting costs full; clay -> stand survives a short break; tolerant)")
    print(f"    B: crop=cotton   L_reseed x{mb['l_reseed']:.2f}  L_delay x{mb['l_delay']:.2f}  "
          f"alpha x{mb['alpha']:.2f}   (borewell -> waiting is cheap; sandy -> bed dries fast; averse)")
    print()
    assert da.recommendation != db.recommendation, (
        "worked example is only meaningful if the two profiles disagree"
    )
    assert da.probabilities == db.probabilities == dict(prior.probabilities)

    # ---- isolate: is the flip the crop, or the profile? -----------------
    _bar("CONTROL -- Profile B's situation on soybean (A's crop)")
    pd_ctrl = decide_for_profile(prior, base_a, PROFILE_B_ON_A_CROP)
    dc = pd_ctrl.decision
    print(f"  {PROFILE_B_ON_A_CROP.label}")
    print(f"    E[SOW]={dc.e_loss_sow:,.0f}  E[WAIT]={dc.e_loss_wait:,.0f}  "
          f"-> {dc.recommendation.upper()}  (robust={dc.robust})")
    print()
    print(f"  Profile B's fields land on {dc.recommendation.upper()} even with soybean")
    print(f"  underneath -- so the flip vs Profile A is driven by the profile "
          f"(irrigation/soil/risk), not just the choice of crop.")
    assert dc.recommendation == db.recommendation, (
        "expected Profile B's situation to give the same call regardless of crop"
    )
    print()

    # ---- the already-sown profile: different action set ------------------
    _bar("PROFILE C -- already sown: SOW/WAIT does not apply")
    pc = decide_for_profile(prior, base_a, PROFILE_C)
    print(pc.summary())
    assert pc.decision is None
    print()

    # ---- farmer-facing advisory, unchanged by profile ------------------
    _bar("ADVISORY EVIDENCE IS PROFILE-INDEPENDENT")
    for label, pd_ in decisions.items():
        assert tuple(pd_.decision.evidence_lines) == tuple(advisory_evidence_lines(prior))
    print("  advisory_evidence_lines(prior) is the ONLY evidence source (D-19).")
    print("  Verified identical for base, Profile A, Profile B:")
    for line in advisory_evidence_lines(prior):
        print(f"    - {line}")
    print()
    print("  A profile changes the recommendation and the rupee losses shown.")
    print("  It never changes which evidence lines are eligible to display.")
    print()

    _bar("DISCLOSURE")
    print("  All profiles are ILLUSTRATIVE DEMO profiles, not real registered users.")
    print("  Profile multiplier tables are illustrative directions/magnitudes, NOT")
    print("  calibrated to surveyed farm economics -- same standard as the D-20")
    print("  crop-loss thresholds. Every DecisionResult still carries")
    print(f"  uses_unverified_parameters={base_res.uses_unverified_parameters}.")


if __name__ == "__main__":
    main()

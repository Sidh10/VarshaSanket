"""Stage 4, per-farmer layer -- profile inputs that move the LOSS side ONLY.

WHAT THIS ADDS, AND THE ONE LINE IT MUST NOT CROSS
-------------------------------------------------
Stage 4's `decide()` already compares E[loss|SOW] against E[loss|WAIT] over
Stage 1's full {active, break, transition} distribution. This module lets a
farmer's own situation -- crop, whether they have irrigation, their soil, how
much risk they can absorb -- change the *rupee losses* in that comparison. It
does **not** touch a single probability.

  * Stage 1's `probabilities` / `ci_lower` / `ci_upper` are passed straight into
    `decide()` unchanged. This module never reads them, never scales them, never
    constructs a `RegimePrior`.
  * A `FarmerProfile` is turned into multipliers on `CropEconomics.l_reseed`,
    `l_delay` and `alpha` -- and nothing else -- by `adjusted_economics()`.
  * The adjusted `CropEconomics` goes through the SAME `decide()` as the base
    case, so the SAME `_expected_loss()` / `_assert_is_expectation()` guard runs
    on every profile path. There is no second scoring function here. A profile
    that tried to collapse a branch to a flat number is rejected by that guard
    exactly as the base case would be -- see `check_guard_covers_profile_paths`.

WHY LOSS-SIDE ONLY (the D-C discipline, extended)
------------------------------------------------
D-C: "Both branches carry probability-weighted loss." The probabilities are a
20-year climatological base rate for a calendar date (D-14) -- they describe the
weather, and a farmer's borewell does not change the weather. What a borewell
changes is *what a missed onset costs that farmer*. So every profile field maps
to a loss term:

  irrigation availability -> lowers L_delay
      A rainfed farmer who waits and is wrong loses the whole late-sowing
      penalty. A farmer with an assured borewell can irrigate to establish the
      crop, so the same mistake costs them much less. Waiting is cheaper for
      them; SOW has to clear a lower bar.

  soil type -> modulates alpha (transition share of the reseed loss) and the
      reseed-loss magnitude
      This is the "how a rainfall probability translates to sowing-readiness
      risk" channel. A just-sown seedbed in sandy soil dries out fast, so a
      transition / short-break window is more likely to kill the stand. A
      vertisol (black cotton soil) holds moisture and buffers the same window.
      It changes the LOSS a given regime inflicts, never the regime's
      probability.

  risk preference -> scales EFFECTIVE THETA, by scaling L_reseed
      theta = L_reseed / L_delay is reported, never compared to a probability
      (decision_engine docstring). "Scaling theta" here means scaling the loss
      input and RE-RUNNING the full expected-loss comparison -- not shifting a
      threshold, because there is no threshold. A risk-averse farmer weights the
      cash-destroying outcome (sow, then a break, reseed from savings) more
      heavily: L_reseed up, so E[loss|SOW] up, so WAIT is favoured.

  sowing status / growth stage -> selects WHICH DECISION APPLIES
      "Sow now or wait" is only a question before the seed is in the ground.
      A farmer whose crop is already up faces a different decision entirely
      (protect the standing crop / contingency irrigation), with a different
      action set and different losses. That decision is NOT modelled in Stage 4
      today. `decide_for_profile()` recognises the difference and declines to
      emit a SOW/WAIT recommendation for an already-sown farmer, rather than
      forcing the pre-sowing model onto a situation it does not describe.

EVERYTHING HERE IS ILLUSTRATIVE (same standard as the crop-loss thresholds)
--------------------------------------------------------------------------
D-20: the base `CropEconomics` rupee values are illustrative and untraced, every
`DecisionResult` from them carries `uses_unverified_parameters=True`. The
profile multiplier tables below are illustrative too -- they are plausible
directions and rough magnitudes, NOT calibrated to surveyed farm economics.
`FarmerProfile.profile_is_illustrative` is always True and is surfaced in the
output. Profiles are named "Demo profile A/B/...", never as real registered
users -- there is no farmer database and this is not one.

ADVISORY TEXT IS UNCHANGED BY PROFILE
------------------------------------
`decide()` sources farmer-facing evidence from `advisory_evidence_lines(prior)`
(the D-19 boundary) and nothing here changes that. A profile changes the
recommendation and the rupee numbers shown; it never changes which evidence
lines are eligible to display. `check_guard_covers_profile_paths` asserts the
evidence lines are byte-identical across every profile.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from src.models.climatological_prior import RegimePrior, advisory_evidence_lines
from src.models.decision_engine import (
    CropEconomics,
    DecisionResult,
    _loss_vectors,
    decide,
)

# ---------------------------------------------------------------------------
# The profile fields. Enums, so an out-of-range value fails at construction
# rather than silently indexing a default.
# ---------------------------------------------------------------------------


class SowingStatus(str, Enum):
    PRE_SOWING = "pre_sowing"   # seed not yet in the ground -> SOW vs WAIT applies
    SOWN = "sown"               # crop already up -> a different decision applies


class GrowthStage(str, Enum):
    """Only meaningful once SOWN. A PRE_SOWING profile must carry NOT_APPLICABLE
    so a stage can never be attached to a farmer with no crop in the ground."""

    NOT_APPLICABLE = "not_applicable"
    GERMINATION = "germination"
    VEGETATIVE = "vegetative"
    REPRODUCTIVE = "reproductive"


class IrrigationAccess(str, Enum):
    RAINFED = "rainfed"    # no supplemental water; a missed onset costs the full penalty
    PARTIAL = "partial"    # one saving irrigation possible (tank / limited well)
    ASSURED = "assured"    # borewell / canal; a missed onset is largely recoverable


class SoilType(str, Enum):
    SANDY = "sandy"        # low water-holding capacity; a just-sown bed dries fast
    LOAM = "loam"          # medium retention -- the reference
    CLAY = "clay"          # vertisol / black cotton; holds moisture, buffers a short break


class RiskPreference(str, Enum):
    RISK_TOLERANT = "risk_tolerant"   # can absorb a reseed; weights a missed window more
    NEUTRAL = "neutral"
    RISK_AVERSE = "risk_averse"        # a reseed comes out of savings; weights it more


# ---------------------------------------------------------------------------
# Illustrative multiplier tables. NOT calibrated to surveyed farm economics.
#
# Invariants that keep the D-C guard load-bearing on every profile path:
#   * every value is strictly positive (no zero, no negative)
#   * the reference level of each field is EXACTLY 1.0, so an all-reference
#     profile reproduces the base `decide()` result bit-for-bit
#     (asserted in check_reference_profile_is_identity)
#   * bounded well away from 0, so no product can drive l_reseed / l_delay to 0
#     and collapse a loss vector to a constant
# ---------------------------------------------------------------------------

# Irrigation lowers L_delay only. Waiting and being wrong (rains were active,
# you missed the window) is cheaper when you can irrigate to catch up.
_IRRIGATION_L_DELAY_FACTOR: dict[IrrigationAccess, float] = {
    IrrigationAccess.RAINFED: 1.00,
    IrrigationAccess.PARTIAL: 0.80,
    IrrigationAccess.ASSURED: 0.55,
}

# Soil retention modulates the TRANSITION share of the reseed loss (alpha):
# a marginal window hurts a fast-draining seedbed more.
_SOIL_ALPHA_FACTOR: dict[SoilType, float] = {
    SoilType.SANDY: 1.35,
    SoilType.LOAM: 1.00,
    SoilType.CLAY: 0.70,
}
# ... and the reseed-loss magnitude, more mildly (a failed stand on sandy soil
# tends to fail harder / need a cleaner reseed).
_SOIL_L_RESEED_FACTOR: dict[SoilType, float] = {
    SoilType.SANDY: 1.15,
    SoilType.LOAM: 1.00,
    SoilType.CLAY: 0.90,
}

# Risk preference scales effective theta by scaling L_reseed (the numerator).
_RISK_L_RESEED_FACTOR: dict[RiskPreference, float] = {
    RiskPreference.RISK_TOLERANT: 0.77,
    RiskPreference.NEUTRAL: 1.00,
    RiskPreference.RISK_AVERSE: 1.30,
}

# alpha must stay a genuine partial share in (0, 1); clamp defensively so a
# future table edit cannot push it to >= 1 (which would make a transition
# window cost MORE than an outright break -- incoherent, though the structural
# guard would still pass).
_ALPHA_CEILING = 0.95


@dataclass(frozen=True)
class FarmerProfile:
    """An ILLUSTRATIVE DEMO farmer. Not a real registered user.

    There is no farmer database behind this. `label` is "Demo profile A" or
    similar and must not be a real person's name. `profile_is_illustrative` is
    always True and is rendered in the output next to the recommendation, the
    same way the provisional-cost disclosure is (D-20).
    """

    label: str
    crop: str
    sowing_status: SowingStatus
    irrigation: IrrigationAccess
    soil: SoilType
    risk: RiskPreference
    growth_stage: GrowthStage = GrowthStage.NOT_APPLICABLE
    profile_is_illustrative: bool = True

    def __post_init__(self) -> None:
        if not self.profile_is_illustrative:
            raise ValueError(
                "FarmerProfile.profile_is_illustrative cannot be set False -- "
                "these are demo profiles, not real users (D-20 disclosure standard)."
            )
        pre = self.sowing_status is SowingStatus.PRE_SOWING
        na = self.growth_stage is GrowthStage.NOT_APPLICABLE
        if pre and not na:
            raise ValueError(
                f"{self.label}: a PRE_SOWING profile has no crop in the ground and "
                f"cannot carry growth_stage={self.growth_stage.value!r}."
            )
        if not pre and na:
            raise ValueError(
                f"{self.label}: a SOWN profile must carry a real growth_stage, "
                f"not NOT_APPLICABLE."
            )


# ---------------------------------------------------------------------------
# Applicability -- which decision even applies
# ---------------------------------------------------------------------------

SOW_VS_WAIT = "sow_vs_wait"
POST_SOWING_NOT_MODELLED = "post_sowing_contingency_not_modelled"


def decision_applicability(profile: FarmerProfile) -> str:
    """Pre-sowing and already-sown are DIFFERENT action sets, not the same one
    with different numbers.

      PRE_SOWING -> `SOW_VS_WAIT`: sow now vs wait for a clearer signal. This is
        the decision Stage 4 models.

      SOWN -> `POST_SOWING_NOT_MODELLED`: the seed is in the ground, so "sow or
        wait" is moot. The live decision is whether to spend on protecting the
        standing crop (contingency irrigation, mulching) against a forecast
        break, weighed against the stage-dependent value at risk. That action
        set and its losses are not modelled in Stage 4 today; `decide_for_profile`
        returns no recommendation rather than misapplying the pre-sowing model.
    """
    if profile.sowing_status is SowingStatus.PRE_SOWING:
        return SOW_VS_WAIT
    return POST_SOWING_NOT_MODELLED


# ---------------------------------------------------------------------------
# The loss-side adjustment. The ONLY thing this module does to the numbers.
# ---------------------------------------------------------------------------


def profile_multipliers(profile: FarmerProfile) -> dict[str, float]:
    """The three loss-side multipliers this profile implies. Pure lookup.

    Returned as a dict so the worked example can show exactly which field moved
    which term. Keys: `l_reseed`, `l_delay`, `alpha`.
    """
    return {
        "l_reseed": (
            _SOIL_L_RESEED_FACTOR[profile.soil]
            * _RISK_L_RESEED_FACTOR[profile.risk]
        ),
        "l_delay": _IRRIGATION_L_DELAY_FACTOR[profile.irrigation],
        "alpha": _SOIL_ALPHA_FACTOR[profile.soil],
    }


def adjusted_economics(base: CropEconomics, profile: FarmerProfile) -> CropEconomics:
    """Apply the profile's loss-side multipliers to `base`.

    Returns a new frozen `CropEconomics`. Reads NO probability and constructs NO
    RegimePrior. `verified` stays whatever `base` had (the ICAR gap does not
    close because a farmer has a borewell). The `source` string gains an
    explicit note that an illustrative profile adjustment was applied.
    """
    if profile.crop != base.crop:
        raise ValueError(
            f"profile crop {profile.crop!r} != economics crop {base.crop!r}"
        )

    m = profile_multipliers(profile)
    l_reseed = base.l_reseed * m["l_reseed"]
    l_delay = base.l_delay * m["l_delay"]
    alpha = min(base.alpha * m["alpha"], _ALPHA_CEILING)

    # Guard-safety, asserted not assumed: the tables above are all strictly
    # positive, so this should never trip -- but a future edit could add a 0 or
    # a negative, and that must fail HERE (loudly) rather than sail into
    # _assert_is_expectation as a collapsed loss vector.
    if not (l_reseed > 0.0 and l_delay > 0.0 and 0.0 < alpha < 1.0):
        raise ValueError(
            f"{profile.label}: profile adjustment produced a non-positive / "
            f"out-of-range loss term (l_reseed={l_reseed}, l_delay={l_delay}, "
            f"alpha={alpha}). _assert_is_expectation would reject the resulting "
            f"branch; fix the multiplier table, do not special-case."
        )

    return replace(
        base,
        l_reseed=l_reseed,
        l_delay=l_delay,
        alpha=alpha,
        source=base.source + " | + ILLUSTRATIVE farmer-profile loss adjustment (D-26)",
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfileDecision:
    profile: FarmerProfile
    applicability: str
    decision: DecisionResult | None      # None when the action set is not SOW/WAIT
    base_theta: float
    effective_theta: float | None
    multipliers: dict[str, float]
    not_modelled_reason: str | None
    profile_is_illustrative: bool = True

    def summary(self) -> str:
        head = (
            f"{self.profile.label}  [ILLUSTRATIVE DEMO PROFILE -- not a real user]\n"
            f"  crop={self.profile.crop}  sowing={self.profile.sowing_status.value}  "
            f"irrigation={self.profile.irrigation.value}  soil={self.profile.soil.value}  "
            f"risk={self.profile.risk.value}"
        )
        if self.decision is None:
            return (
                head
                + f"\n  growth_stage={self.profile.growth_stage.value}"
                + f"\n  applicability: {self.applicability}"
                + f"\n  -> NO SOW/WAIT RECOMMENDATION. {self.not_modelled_reason}"
            )
        d = self.decision
        return (
            head
            + f"\n  loss multipliers: L_reseed x{self.multipliers['l_reseed']:.2f}  "
            f"L_delay x{self.multipliers['l_delay']:.2f}  alpha x{self.multipliers['alpha']:.2f}"
            + f"\n  theta: base {self.base_theta:.3f} -> effective {self.effective_theta:.3f}  "
            f"(reported, NOT a threshold)"
            + f"\n  E[loss|SOW] = {d.e_loss_sow:>10,.0f} INR/ha    "
            f"E[loss|WAIT] = {d.e_loss_wait:>10,.0f} INR/ha"
            + f"\n  RECOMMENDATION: {d.recommendation.upper()}  "
            f"(margin E[wait]-E[sow] = {d.margin:+,.0f}; robust={d.robust})"
        )


def decide_for_profile(
    prior: RegimePrior,
    base: CropEconomics,
    profile: FarmerProfile,
) -> ProfileDecision:
    """Run the Stage 4 decision for one illustrative farmer profile.

    PRE_SOWING  -> adjust the LOSS side per the profile, then call the EXISTING
                   `decide()` over Stage 1's UNCHANGED distribution.
    SOWN        -> return a ProfileDecision with `decision=None`; the relevant
                   action set is not modelled (see `decision_applicability`).
    """
    applic = decision_applicability(profile)

    if applic != SOW_VS_WAIT:
        return ProfileDecision(
            profile=profile,
            applicability=applic,
            decision=None,
            base_theta=base.theta,
            effective_theta=None,
            multipliers=profile_multipliers(profile),
            not_modelled_reason=(
                "This farmer has already sown; the live decision is whether to "
                "protect the standing crop against a forecast break "
                f"(crop at {profile.growth_stage.value}), which is a different "
                "action set with different losses. Stage 4 models the pre-sowing "
                "SOW/WAIT decision only. Emitting a SOW/WAIT recommendation here "
                "would misapply the model."
            ),
        )

    econ = adjusted_economics(base, profile)
    result = decide(prior, econ)  # <-- existing engine, existing _assert_is_expectation

    # The D-19 boundary is inherited through decide(); assert the profile did
    # not perturb it. (decide() sets evidence_lines from advisory_evidence_lines.)
    boundary = tuple(advisory_evidence_lines(prior))
    if tuple(result.evidence_lines) != boundary:
        raise ValueError(
            f"{profile.label}: evidence lines diverged from the D-19 boundary. "
            f"A profile must never change which evidence is shown.\n"
            f"  boundary: {boundary}\n  result:   {result.evidence_lines}"
        )

    return ProfileDecision(
        profile=profile,
        applicability=applic,
        decision=result,
        base_theta=base.theta,
        effective_theta=econ.theta,
        multipliers=profile_multipliers(profile),
        not_modelled_reason=None,
    )


# ---------------------------------------------------------------------------
# Guard / boundary verification -- run against every new code path
# ---------------------------------------------------------------------------


def _reference_profile(crop: str, label: str = "reference") -> FarmerProfile:
    """The all-reference profile: every multiplier is exactly 1.0."""
    return FarmerProfile(
        label=label,
        crop=crop,
        sowing_status=SowingStatus.PRE_SOWING,
        irrigation=IrrigationAccess.RAINFED,
        soil=SoilType.LOAM,
        risk=RiskPreference.NEUTRAL,
    )


def check_reference_profile_is_identity(prior: RegimePrior, base: CropEconomics) -> None:
    """An all-reference profile must reproduce the base `decide()` bit-for-bit.

    If it does not, a multiplier table has a reference level that is not 1.0 and
    every profile result is silently offset from the base case.
    """
    ref = _reference_profile(base.crop)
    m = profile_multipliers(ref)
    assert m == {"l_reseed": 1.0, "l_delay": 1.0, "alpha": 1.0}, m

    base_res = decide(prior, base)
    prof_res = decide_for_profile(prior, base, ref).decision
    assert prof_res is not None
    assert np.isclose(prof_res.e_loss_sow, base_res.e_loss_sow, atol=1e-9)
    assert np.isclose(prof_res.e_loss_wait, base_res.e_loss_wait, atol=1e-9)
    assert prof_res.recommendation == base_res.recommendation
    assert tuple(prof_res.evidence_lines) == tuple(base_res.evidence_lines)
    print("  all-reference profile == base decide()      : YES "
          f"(E[sow] {base_res.e_loss_sow:,.1f}, E[wait] {base_res.e_loss_wait:,.1f})")


def check_guard_covers_profile_paths(prior: RegimePrior, base: CropEconomics) -> None:
    """Every profile path goes through _expected_loss / _assert_is_expectation,
    and a profile that would collapse a branch is REJECTED, not shipped.
    """
    print("=" * 78)
    print("D-C GUARD CHECK -- profile paths")
    print("=" * 78)

    # 1. The full pre-sowing grid: 3 irrigation x 3 soil x 3 risk = 27 combos.
    #    Each must route through decide() (hence _expected_loss x4) and yield
    #    two genuine, non-constant loss vectors, with evidence unchanged.
    boundary = tuple(advisory_evidence_lines(prior))
    n = 0
    for irr in IrrigationAccess:
        for soil in SoilType:
            for risk in RiskPreference:
                p = FarmerProfile(
                    label=f"grid[{irr.value},{soil.value},{risk.value}]",
                    crop=base.crop,
                    sowing_status=SowingStatus.PRE_SOWING,
                    irrigation=irr,
                    soil=soil,
                    risk=risk,
                )
                pd_ = decide_for_profile(prior, base, p)
                assert pd_.decision is not None
                econ = adjusted_economics(base, p)
                sow_v, wait_v = _loss_vectors(econ)
                # neither branch may be constant across regimes
                assert not np.allclose(sow_v, sow_v[0]), (p.label, sow_v)
                assert not np.allclose(wait_v, wait_v[0]), (p.label, wait_v)
                # _expected_loss would have raised inside decide() otherwise;
                # this re-asserts the structural property directly.
                assert tuple(pd_.decision.evidence_lines) == boundary
                n += 1
    print(f"  {n} pre-sowing profile combinations")
    print(f"    - all routed through decide() -> _expected_loss -> _assert_is_expectation")
    print(f"    - both loss vectors non-constant in every combination")
    print(f"    - farmer-facing evidence lines identical across all {n} (D-19 intact)")

    # 2. A profile-shaped adjustment that DOES collapse a branch must be
    #    rejected by _assert_is_expectation, exactly as the base case is.
    #    (Not constructible through the real tables -- shown at the econ level.)
    collapsed = replace(base, l_reseed=0.0)  # SOW vector -> [0, 0, 0]
    try:
        decide(prior, collapsed)
        raise AssertionError("GUARD FAILED: a collapsed SOW branch was accepted")
    except ValueError as e:
        print(f"  collapsed-branch adjustment rejected        : YES")
        print(f"    -> {str(e)[:92]}...")

    # 3. And the adjustment layer catches a zeroed multiplier BEFORE decide(),
    #    with a message that says fix the table, not special-case.
    import src.models.farmer_profile as fp

    saved = dict(fp._SOIL_L_RESEED_FACTOR)
    try:
        fp._SOIL_L_RESEED_FACTOR[SoilType.LOAM] = 0.0
        bad = FarmerProfile(
            label="tampered", crop=base.crop,
            sowing_status=SowingStatus.PRE_SOWING,
            irrigation=IrrigationAccess.RAINFED, soil=SoilType.LOAM,
            risk=RiskPreference.NEUTRAL,
        )
        try:
            adjusted_economics(base, bad)
            raise AssertionError("GUARD FAILED: a zeroed multiplier passed adjustment")
        except ValueError as e:
            print(f"  zeroed multiplier caught at adjustment       : YES")
            print(f"    -> {str(e)[:92]}...")
    finally:
        fp._SOIL_L_RESEED_FACTOR.clear()
        fp._SOIL_L_RESEED_FACTOR.update(saved)
    print()


def check_d19_boundary() -> None:
    """AST check: this module reads farmer-facing evidence ONLY via
    `advisory_evidence_lines`, never a raw evidence field -- the same guarantee
    `run_stage4_decision.check_d19_boundary` enforces on `decision_engine`.
    """
    import ast
    import inspect

    import src.models.farmer_profile as mod

    print("=" * 78)
    print("D-19 BOUNDARY CHECK -- farmer_profile.py (by AST inspection)")
    print("=" * 78)
    tree = ast.parse(inspect.getsource(mod))
    imported = {
        a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
        for a in n.names
    }
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    raw_fields = {
        "advisory_evidence",
        "evidence_source",
        "seasonal_analog_evidence",
        "seasonal_analog_years",
        "seasonal_analog_detail",
        "seasonal_analog_effective_n",
        "seasonal_analog_agreement",
    }
    leaked = sorted(raw_fields & attrs)
    print(f"  imports advisory_evidence_lines : {'advisory_evidence_lines' in imported}")
    print(f"  calls   advisory_evidence_lines : {'advisory_evidence_lines' in called}")
    print(f"  raw evidence fields read directly: {leaked or 'NONE'}")
    assert "advisory_evidence_lines" in imported
    assert "advisory_evidence_lines" in called
    assert not leaked, f"farmer_profile reads raw evidence fields: {leaked}"

    # Also: no probability field is read anywhere in this module.
    prob_fields = {"probabilities", "ci_lower", "ci_upper"}
    prob_leaked = sorted(prob_fields & attrs)
    # `probabilities` is allowed ONLY in the two immutability-check assertions;
    # confirm it is not read in adjusted_economics / decide_for_profile.
    core = inspect.getsource(adjusted_economics) + inspect.getsource(decide_for_profile) \
        + inspect.getsource(profile_multipliers)
    core_attrs = {n.attr for n in ast.walk(ast.parse(core)) if isinstance(n, ast.Attribute)}
    assert not (prob_fields & core_attrs), (
        f"adjusted_economics / decide_for_profile read a probability field: "
        f"{sorted(prob_fields & core_attrs)}"
    )
    print(f"  probability fields read in adjust/decide core: NONE "
          f"(module-wide, only in immutability asserts: {prob_leaked})")
    print("  -> the profile layer moves losses only; probabilities are inaccessible to it.\n")


def check_probabilities_untouched(prior: RegimePrior, base: CropEconomics) -> None:
    """No profile path may alter Stage 1's probabilities or CI. Assert it across
    the grid by comparing the DecisionResult's echoed distribution to the prior.
    """
    print("=" * 78)
    print("STAGE 1 IMMUTABILITY CHECK -- probabilities are never touched")
    print("=" * 78)
    ref_p = dict(prior.probabilities)
    seen = 0
    for irr in IrrigationAccess:
        for soil in SoilType:
            for risk in RiskPreference:
                p = FarmerProfile(
                    label="imm", crop=base.crop,
                    sowing_status=SowingStatus.PRE_SOWING,
                    irrigation=irr, soil=soil, risk=risk,
                )
                r = decide_for_profile(prior, base, p).decision
                assert r is not None
                assert r.probabilities == ref_p, (p, r.probabilities, ref_p)
                seen += 1
    print(f"  {seen} profiles: DecisionResult.probabilities == prior.probabilities exactly")
    print(f"  prior P: " + "  ".join(f"{k}={v:.4f}" for k, v in ref_p.items()))
    print()

"""Stage 4 per-farmer profile demo data. Backs the `/profiles` screen in
`src/demo/server.py`.

FOUR ILLUSTRATIVE DEMO PROFILES, NOT REAL USERS -- same standard as
`farmer_profile.py` (D-26). Chosen to span the meaningful combinations already
exercised in the Stage 4 worked example (`run_stage4_profile.py`):

  A -- rainfed, black-soil (clay), risk-tolerant soybean smallholder.
       Field-for-field identical to that script's PROFILE_A. -> SOW, but
       FRAGILE (the envelope straddles the call) -- the only combination in
       the whole 3-crop x 27-combo grid for this date that ever recommends
       SOW at all (checked against the live 2018-07-15 case; see profiles
       grid dump in DISCUSSION.md D-27).

  B -- irrigated (assured), sandy-soil, risk-averse cotton grower. Field-for-
       field identical to that script's PROFILE_B. -> WAIT, robust.

  C -- same crop and soil as A (soybean, black/clay soil) and the same
       risk-tolerant preference, but PARTIAL irrigation instead of rainfed.
       A NEW combination (not in the worked example), chosen deliberately: of
       the 81 pre-sowing combinations across all three crops for this prior
       (checked directly against the live 2018-07-15 case; see the grid dump
       in DISCUSSION.md D-27), it has the smallest |margin| of any
       non-SOW combination (E[wait]-E[sow] ~ -183 INR/ha) -- the closest this
       prior comes to a genuine tie -- and is itself FRAGILE. Its
       recommendation LABEL is WAIT, same as B, because the SOW/WAIT space is
       binary and A already occupies the grid's only SOW-shaped corner for
       this date -- a third profile cannot hold a third *label*. What C shows
       instead is a third *outcome shape*: neither A's clean-if-fragile SOW
       nor B's robust WAIT, but a near-flip so close that one small input
       change (partial irrigation instead of rainfed) is enough to cross it.
       That is the honest reading of "a different SOW/WAIT outcome," and is
       flagged as such here rather than silently claimed as a third
       recommendation value.

  D -- crop already sown (germination stage), partial irrigation, loam soil,
       neutral risk. Field-for-field identical to that script's PROFILE_C.
       decision_applicability() routes this to POST_SOWING_NOT_MODELLED, so
       `decide_for_profile` returns no SOW/WAIT recommendation. The UI must
       render that as a deliberate "different decision applies" state, not
       as an error or a blank card.

All four route through the SAME `decide_for_profile` as the worked example,
against the SAME cached 2018-07-15 prior `src/demo/case.py` already builds
for the single-case screen. No new prior is constructed here.

FREE SELECTION (D-28) -- SAME FIELDS, SAME PATH, NO NEW REACHABLE CODE
---------------------------------------------------------------------
The four presets above are now one-click shortcuts on a screen that also lets
the operator choose each field directly. `build_profile_from_fields()` turns a
set of chosen values into a `FarmerProfile`; `_payload_for_profile()` is the
SINGLE function that takes any `FarmerProfile` -- preset or chosen -- to a
payload. There is exactly one `decide_for_profile()` call site in this module,
and both resolvers reach it.

**Nothing the selectors can express is a new code path**, and that is a
countable claim, not a hope:

  * The option lists are generated from the schema itself -- `IrrigationAccess`,
    `SoilType`, `RiskPreference`, `SowingStatus`, `GrowthStage` and the keys of
    `CROP_DEFAULTS` (see `profile_option_values()`). No literal option value is
    written in the UI, so the UI cannot offer a value the schema does not have.
  * The decision-bearing selectors are crop (3) x irrigation (3) x soil (3) x
    risk (3) = **81 pre-sowing combinations** -- exactly the grid dumped against
    the live 2018-07-15 prior in D-27, whose per-crop 27-combo slices are what
    `check_guard_covers_profile_paths` drives through `_expected_loss()` /
    `_assert_is_expectation()` (D-26).
  * Adding `sowing_status=sown` x growth stage (3 real stages) gives 243 further
    combinations, but every one of them short-circuits in
    `decision_applicability()` -> `POST_SOWING_NOT_MODELLED` and returns before
    `adjusted_economics()` or `decide()` is called at all. (`profile_multipliers()`
    -- a pure table lookup -- still runs; no economics, no expectation, no
    decision.) So they add no numeric path either.
  * The remaining 324 of the 648 combinations the enums can express are the ones
    `FarmerProfile.__post_init__` rejects (pre-sowing carrying a real stage;
    sown carrying `NOT_APPLICABLE`). Those are surfaced as plain-language
    validation messages, never as a raw exception -- see
    `ProfileValidationError`.
  * `src/demo/run_profiles_demo.py` drives all 648 through the real HTTP
    endpoint every run, so this paragraph is re-verified rather than trusted.

The coherence rule itself is NOT reimplemented here. `FarmerProfile.__post_init__`
remains the only place that decides whether a combination is valid; this module
catches its `ValueError` and chooses the wording.
"""

from __future__ import annotations

from src.delivery.advisory import render
from src.delivery.risk_display import build_indicator
from src.demo.case import DemoCase
from src.models.decision_engine import CROP_DEFAULTS
from src.models.farmer_profile import (
    FarmerProfile,
    GrowthStage,
    IrrigationAccess,
    RiskPreference,
    SoilType,
    SowingStatus,
    adjusted_economics,
    decide_for_profile,
)

PROFILE_A = FarmerProfile(
    label="Demo profile A -- rainfed black-soil soybean smallholder",
    crop="soybean",
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.RAINFED,
    soil=SoilType.CLAY,
    risk=RiskPreference.RISK_TOLERANT,
)

PROFILE_B = FarmerProfile(
    label="Demo profile B -- irrigated sandy-plot cotton grower",
    crop="cotton",
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.ASSURED,
    soil=SoilType.SANDY,
    risk=RiskPreference.RISK_AVERSE,
)

PROFILE_C = FarmerProfile(
    label="Demo profile C -- same soybean/black-soil/risk-tolerant farmer as "
    "A, but with partial irrigation (near-tie call)",
    crop="soybean",
    sowing_status=SowingStatus.PRE_SOWING,
    irrigation=IrrigationAccess.PARTIAL,
    soil=SoilType.CLAY,
    risk=RiskPreference.RISK_TOLERANT,
)

PROFILE_D = FarmerProfile(
    label="Demo profile D -- crop already sown, at germination",
    crop="soybean",
    sowing_status=SowingStatus.SOWN,
    irrigation=IrrigationAccess.PARTIAL,
    soil=SoilType.LOAM,
    risk=RiskPreference.NEUTRAL,
    growth_stage=GrowthStage.GERMINATION,
)

DEMO_PROFILES: dict[str, FarmerProfile] = {
    "A": PROFILE_A,
    "B": PROFILE_B,
    "C": PROFILE_C,
    "D": PROFILE_D,
}

# The label every freely-chosen profile carries. Same standard as the presets:
# it must read as an illustrative demo profile and must never look like a real
# person or a registered user (D-20/D-26).
CUSTOM_PROFILE_LABEL = "Custom demo profile (illustrative -- not a real user)"


class ProfileValidationError(ValueError):
    """A combination the SCHEMA rejects, phrased for a person to read.

    Raised for a value that is not in the enum, a crop with no cost parameters,
    or a `sowing_status`/`growth_stage` pair that `FarmerProfile.__post_init__`
    refuses. The HTTP layer turns this into a 400 with the message; it never
    surfaces a traceback or a raw exception repr.
    """


# Cosmetic one-line hints for the selectors. `.get()` with an empty default on
# purpose: the option VALUES come from the enums (below), so a future enum
# member appears in the UI immediately, just without a hint -- it can never be
# silently dropped from the list because a hint was forgotten.
_OPTION_HINTS: dict[str, str] = {
    "rainfed": "no supplemental water -- a missed onset costs the full penalty",
    "partial": "one saving irrigation possible (tank / limited well)",
    "assured": "borewell or canal -- a missed onset is largely recoverable",
    "sandy": "low water-holding capacity; a just-sown bed dries fast",
    "loam": "medium retention -- the reference soil",
    "clay": "vertisol / black cotton; holds moisture, buffers a short break",
    "risk_tolerant": "can absorb a reseed",
    "neutral": "the reference",
    "risk_averse": "a reseed would come out of savings",
    "pre_sowing": "seed not yet in the ground -- SOW vs WAIT applies",
    "sown": "crop already up -- a different decision applies",
    "not_applicable": "only coherent before sowing",
    "germination": "just emerged",
    "vegetative": "in leaf",
    "reproductive": "flowering / pod or boll fill",
}


def _option(value: str) -> dict[str, str]:
    """One selector option, derived from the schema value itself."""
    return {
        "value": value,
        "label": value.replace("_", " "),
        "hint": _OPTION_HINTS.get(value, ""),
    }


def profile_option_values() -> dict[str, list[dict[str, str]]]:
    """The selector options, GENERATED FROM THE SCHEMA -- never hand-written.

    The UI renders exactly these and holds no option literals of its own, so it
    is structurally incapable of offering a crop or an enum value the schema
    does not define. Crop is not an enum on `FarmerProfile` (it is a plain
    `str`), so its authority is `CROP_DEFAULTS` -- the same dict
    `_payload_for_profile` looks the base economics up in, so an offered crop
    always has cost parameters behind it.
    """
    return {
        "crop": [_option(c) for c in sorted(CROP_DEFAULTS)],
        "sowing_status": [_option(m.value) for m in SowingStatus],
        "irrigation": [_option(m.value) for m in IrrigationAccess],
        "soil": [_option(m.value) for m in SoilType],
        "risk": [_option(m.value) for m in RiskPreference],
        "growth_stage": [_option(m.value) for m in GrowthStage],
        # Which growth stages are coherent once SOWN, and which sowing status
        # is the one that needs a stage at all. Served so the UI mirrors the
        # constructor's rule without writing any schema value of its own;
        # ENFORCEMENT still lives only in FarmerProfile.__post_init__.
        "growth_stage_when_sown": [
            _option(m.value) for m in GrowthStage if m is not GrowthStage.NOT_APPLICABLE
        ],
        "growth_stage_when_pre_sowing": GrowthStage.NOT_APPLICABLE.value,
        "sowing_status_requiring_stage": SowingStatus.SOWN.value,
    }


def demo_preset_summaries() -> list[dict]:
    """The four presets as plain field values, in display order.

    Served to the UI so that clicking a preset can set the selectors from the
    `FarmerProfile` objects themselves. The UI therefore holds no copy of a
    preset's fields -- if a preset is edited here, the card and the selectors it
    populates both follow, and they cannot drift apart.
    """
    return [_profile_block(key, profile) for key, profile in DEMO_PROFILES.items()]


def _parse_enum(enum_cls, raw: str, field_label: str):
    try:
        return enum_cls(raw)
    except ValueError:
        allowed = ", ".join(m.value for m in enum_cls)
        raise ProfileValidationError(
            f"{field_label} '{raw}' is not one of the values this demo supports. "
            f"Choose one of: {allowed}."
        ) from None


def build_profile_from_fields(
    crop: str,
    sowing_status: str,
    irrigation: str,
    soil: str,
    risk: str,
    growth_stage: str | None = None,
) -> FarmerProfile:
    """Turn chosen field values into a `FarmerProfile`, or explain why not.

    Raises `ProfileValidationError` -- with a message a person can act on --
    for an unknown value, a crop with no cost parameters, or a combination
    `FarmerProfile.__post_init__` rejects.

    The coherence rule is NOT re-derived here. The constructor decides whether
    a combination raises; the `if` below only picks which wording to show for
    the failure the constructor already produced, and falls back to quoting the
    constructor's own message if a future rule change makes both shapes miss.
    """
    if crop not in CROP_DEFAULTS:
        available = ", ".join(sorted(CROP_DEFAULTS))
        raise ProfileValidationError(
            f"No cost parameters exist for crop '{crop}'. This demo carries "
            f"illustrative economics for: {available}."
        )

    status = _parse_enum(SowingStatus, sowing_status, "Sowing status")
    irr = _parse_enum(IrrigationAccess, irrigation, "Irrigation access")
    soil_type = _parse_enum(SoilType, soil, "Soil type")
    risk_pref = _parse_enum(RiskPreference, risk, "Risk preference")
    stage = _parse_enum(
        GrowthStage,
        growth_stage if growth_stage else GrowthStage.NOT_APPLICABLE.value,
        "Growth stage",
    )

    try:
        return FarmerProfile(
            label=CUSTOM_PROFILE_LABEL,
            crop=crop,
            sowing_status=status,
            irrigation=irr,
            soil=soil_type,
            risk=risk_pref,
            growth_stage=stage,
        )
    except ValueError as exc:
        pre = status is SowingStatus.PRE_SOWING
        na = stage is GrowthStage.NOT_APPLICABLE
        if pre and not na:
            raise ProfileValidationError(
                f"A farmer who has not sown yet has no crop in the ground, so "
                f"'{stage.value.replace('_', ' ')}' is not a stage they can be at. "
                f"Set sowing status to 'sown' first, or leave the growth stage unset."
            ) from None
        if not pre and na:
            raise ProfileValidationError(
                "A farmer who has already sown has a crop in the ground, so it is "
                "at some growth stage. Choose germination, vegetative or reproductive."
            ) from None
        # The constructor rejected this for a reason these two branches do not
        # describe -- quote it rather than invent an explanation or leak a
        # traceback.
        raise ProfileValidationError(
            f"This combination is not a coherent farmer profile: {exc}"
        ) from None


def _base_rate_block(case: DemoCase) -> dict:
    return {
        "probabilities": dict(case.prior.probabilities),
        "ci_lower": dict(case.prior.ci_lower),
        "ci_upper": dict(case.prior.ci_upper),
        "wording": (
            "Based on 20-year averages for this date (2000-2019), "
            "not a forecast for this year."
        ),
    }


def _profile_block(key: str, profile: FarmerProfile) -> dict:
    return {
        "key": key,
        "label": profile.label,
        "crop": profile.crop,
        "sowing_status": profile.sowing_status.value,
        "growth_stage": profile.growth_stage.value,
        "irrigation": profile.irrigation.value,
        "soil": profile.soil.value,
        "risk": profile.risk.value,
        "is_illustrative": profile.profile_is_illustrative,
    }


def build_profile_payload(case: DemoCase, profile_key: str) -> dict:
    """Preset resolver: one of the four rehearsed demo profiles, by key.

    Unchanged entry point -- `run_profiles_demo.py` and
    `/api/profile_decide?profile=<key>` still call exactly this. It resolves a
    key to the `FarmerProfile` object and hands it to `_payload_for_profile`,
    the same function the freely-chosen path uses.
    """
    if profile_key not in DEMO_PROFILES:
        raise ProfileValidationError(
            f"Unknown demo profile '{profile_key}'. Available: "
            f"{', '.join(DEMO_PROFILES)}."
        )
    return _payload_for_profile(case, DEMO_PROFILES[profile_key], profile_key)


def build_custom_profile_payload(
    case: DemoCase,
    crop: str,
    sowing_status: str,
    irrigation: str,
    soil: str,
    risk: str,
    growth_stage: str | None = None,
) -> dict:
    """Free-selection resolver: chosen field values -> the SAME payload path.

    Raises `ProfileValidationError` if the chosen combination is not one the
    schema accepts. Everything past construction is `_payload_for_profile`,
    byte-for-byte the function the presets use -- there is no second decision
    path, and no scoring logic lives here.
    """
    profile = build_profile_from_fields(
        crop=crop,
        sowing_status=sowing_status,
        irrigation=irrigation,
        soil=soil,
        risk=risk,
        growth_stage=growth_stage,
    )
    return _payload_for_profile(case, profile, "custom")


def _payload_for_profile(case: DemoCase, profile: FarmerProfile, key: str) -> dict:
    """Run `decide_for_profile` for ONE profile and shape it for the UI.

    THE single decision path on this screen -- the presets and the free
    selectors both arrive here, so a chosen profile and a preset with identical
    fields cannot diverge. (`run_profiles_demo.py` asserts exactly that.)

    Real pipeline calls only -- `decide_for_profile()` (which calls the real
    `decide()` / `_expected_loss()`), `advisory.render()`,
    `risk_display.build_indicator()`. No lookup table, no shortcut.
    """
    base = CROP_DEFAULTS[profile.crop]
    pd_ = decide_for_profile(case.prior, base, profile)

    payload = {
        "profile": _profile_block(key, profile),
        "applicability": pd_.applicability,
        "base_rate": _base_rate_block(case),
    }

    if pd_.decision is None:
        payload["decision"] = None
        payload["not_modelled_reason"] = pd_.not_modelled_reason
        return payload

    result = pd_.decision
    advisory = render(result, case.prior, "en")
    indicator = build_indicator(result)
    econ_adj = adjusted_economics(base, profile)
    p = result.probabilities

    payload["economics"] = {
        # the farmer's crop default, BEFORE this profile's multipliers
        "base": {"l_reseed": base.l_reseed, "l_delay": base.l_delay, "alpha": base.alpha},
        # the SAME numbers AFTER irrigation/soil/risk multipliers -- what
        # decide() actually ran on for this farmer
        "effective": {
            "l_reseed": econ_adj.l_reseed,
            "l_delay": econ_adj.l_delay,
            "alpha": econ_adj.alpha,
        },
        "multipliers": pd_.multipliers,
        "base_theta": pd_.base_theta,
        "effective_theta": pd_.effective_theta,
    }
    payload["decision"] = {
        "recommendation": result.recommendation,
        "e_loss_sow": result.e_loss_sow,
        "e_loss_wait": result.e_loss_wait,
        "margin": result.margin,
        "robust": result.robust,
        "envelope": {
            k: {"e_sow": v["e_sow"], "e_wait": v["e_wait"], "recommendation": v["recommendation"]}
            for k, v in result.envelope.items()
        },
        "contributions": {
            "regimes": list(p.keys()),
            "prob": [p[c] for c in p],
            "loss_sow": [result.loss_sow[c] for c in p],
            "loss_wait": [result.loss_wait[c] for c in p],
        },
        "uses_unverified_parameters": result.uses_unverified_parameters,
        "disclosure": result.disclosure(),
    }
    payload["advisory"] = {
        "text": advisory.text,
        "language": advisory.language,
        "verified_language": advisory.verified_language,
        "char_count": advisory.char_count,
        "evidence_lines": list(advisory.evidence_lines),
        "disclosure_shown": advisory.disclosure_shown,
    }
    payload["risk"] = {
        "colour": indicator.risk_colour,
        "label": indicator.risk_label,
        "recommendation": indicator.recommendation,
        "robust": indicator.robust,
        "svg": indicator.as_uniform_svg(),
    }
    return payload

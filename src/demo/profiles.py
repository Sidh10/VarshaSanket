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
    """Run `decide_for_profile` for one demo profile and shape it for the UI.

    Real pipeline calls only -- `decide_for_profile()` (which calls the real
    `decide()` / `_expected_loss()`), `advisory.render()`,
    `risk_display.build_indicator()`. No lookup table, no shortcut.
    """
    if profile_key not in DEMO_PROFILES:
        raise ValueError(f"unknown profile key {profile_key!r}; have {list(DEMO_PROFILES)}")
    profile = DEMO_PROFILES[profile_key]
    base = CROP_DEFAULTS[profile.crop]
    pd_ = decide_for_profile(case.prior, base, profile)

    payload = {
        "profile": _profile_block(profile_key, profile),
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

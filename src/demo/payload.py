"""Turn a (DemoCase, l_reseed) into the JSON the demo UI renders.

Every field here is computed by the REAL pipeline functions -- `decide()` (which
calls `_expected_loss()`), `advisory.render()`, `risk_display.build_indicator()`.
There is no precomputed grid; the server calls this on every slider event.

TWO EFFECTIVE-N FIGURES, NEVER MERGED
------------------------------------
`stage1_n_years` and `stage2_analog_effective_n` are different quantities:

  stage1_n_years = 20  -> independent monsoon seasons behind the climatological
                          base rate. A count of real years.
  stage2_analog_effective_n ~ 3.8 -> entropy-based effective size of the K=5
                          nearest-analog set shown as evidence. A concentration
                          measure, not a year count, and NOT a confidence in the
                          probability.

The payload keeps them as separate labelled fields. The UI must not add them,
average them, or fold them into one "confidence" number.

BASE RATE, NOT A FORECAST -- and no skill number
-----------------------------------------------
`base_rate` carries the exact wording already in the advisory: "based on 20-year
averages for this date, not a forecast for this year". There is deliberately no
accuracy / skill / CRPS field: D-14 through D-17 found no honest skill number for
this pipeline, and a manufactured stand-in would defeat the point.
"""

from __future__ import annotations

from src.delivery.advisory import render
from src.delivery.risk_display import build_indicator
from src.demo.case import CROP, TARGET_DATE, DemoCase

# theta thresholds for this case, located empirically (src/demo/run_demo.py
# re-derives and asserts them). Two distinct thresholds:
#   ~0.95 : the point-estimate recommendation flips SOW -> WAIT
#   ~0.75 : below this SOW is ROBUST across the uncertainty envelope; above it
#           the point estimate still says SOW but the envelope straddles the
#           decision (fragile). D-20's "theta ~ 0.75" was this robustness
#           boundary, not the recommendation flip.
THETA_RECOMMENDATION_FLIP = 0.95
THETA_ROBUST_BOUNDARY = 0.75


def build_payload(case: DemoCase, l_reseed: float) -> dict:
    result = case.decide_at(l_reseed)              # <-- real _expected_loss()
    advisory = render(result, case.prior, "en")     # <-- real advisory text
    indicator = build_indicator(result)             # <-- real risk display

    p = result.probabilities
    return {
        "case": {
            "target_date": TARGET_DATE,
            "crop": CROP,
            "l_delay": case.l_delay,
            "l_reseed": result.loss_sow["break"],   # == the slider value
            "theta": result.theta,
        },
        # --- theta slider: the live decision ---
        "decision": {
            "recommendation": result.recommendation,
            "e_loss_sow": result.e_loss_sow,
            "e_loss_wait": result.e_loss_wait,
            "margin": result.margin,                 # E[wait] - E[sow]
            "robust": result.robust,
            "envelope": {
                k: {
                    "e_sow": v["e_sow"],
                    "e_wait": v["e_wait"],
                    "recommendation": v["recommendation"],
                }
                for k, v in result.envelope.items()
            },
            # per-regime contributions, so a judge sees WHY the bars move
            "contributions": {
                "regimes": list(p.keys()),
                "prob": [p[c] for c in p],
                "loss_sow": [result.loss_sow[c] for c in p],
                "loss_wait": [result.loss_wait[c] for c in p],
            },
            "theta_recommendation_flip": THETA_RECOMMENDATION_FLIP,
            "theta_robust_boundary": THETA_ROBUST_BOUNDARY,
        },
        # --- two effective-N figures, structurally separate ---
        "effective_n": {
            "stage1": {
                "label": "Stage 1 - climatology",
                "value": case.stage1_n_years,
                "unit": "monsoon seasons",
                "means": "independent years of observed data behind the base rate",
            },
            "stage2": {
                "label": "Stage 2 - seasonal analogs",
                "value": round(case.stage2_analog_effective_n, 2),
                "unit": "effective analog seasons (of 5 shown)",
                "means": "how concentrated the nearest-analog set is; NOT a confidence in the probability",
                "agreement": case.stage2_analog_agreement,
            },
        },
        # --- Stage 1 base rate + block-bootstrap CI (replaces the old
        #     'backtest number' slot). Base rate, NOT a forecast. No skill number. ---
        "base_rate": {
            "probabilities": dict(p),
            "ci_lower": dict(case.prior.ci_lower),
            "ci_upper": dict(case.prior.ci_upper),
            "wording": (
                "Based on 20-year averages for this date "
                "(2000-2019), not a forecast for this year."
            ),
            "ci_note": (
                "95% interval from block bootstrap over 20 years "
                "(marginal per class; not a joint interval)."
            ),
            "no_skill_number_note": (
                "No accuracy/skill figure is shown: the isolation tests "
                "(D-14 to D-17) found none that is honest for this pipeline."
            ),
        },
        # --- the full advisory, exactly as built in Phase 4b ---
        "advisory": {
            "text": advisory.text,
            "language": advisory.language,
            "verified_language": advisory.verified_language,
            "char_count": advisory.char_count,
            "evidence_lines": list(advisory.evidence_lines),
            "disclosure_shown": advisory.disclosure_shown,
        },
        # --- single-region risk display ---
        "risk": {
            "colour": indicator.risk_colour,
            "label": indicator.risk_label,
            "p_active": indicator.p_active,
            "p_break": indicator.p_break,
            "p_transition": indicator.p_transition,
            "recommendation": indicator.recommendation,
            "robust": indicator.robust,
            "scale_caveat": indicator.scale_caveat,
            "disclosure_needed": indicator.disclosure_needed,
            "svg": indicator.as_uniform_svg(),
        },
    }

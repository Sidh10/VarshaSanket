"""The ONE pre-baked demo case. 2018-07-15, soybean. Nothing else.

WHY THIS DATE AND CROP -- FIXED, NOT A PARAMETER
------------------------------------------------
2018 is the single "leaning" seasonal-analog year in the 2000-2019 record
(D-18/D-19: 19 of 20 years are "divided"). It is the only case where BOTH
farmer-facing evidence lines appear at once:

  * the IMD bulletin trough-position line, and
  * the seasonal-analog line (suppressed for the 19 "divided" years).

It was chosen for exactly this in Stage 4's worked example (D-20). The demo
does not offer a date picker or a crop dropdown -- Phase 5 is "protect the
MVP", and one honestly-working case beats a configurable half-working one.

The ONLY thing that varies at demo time is `l_reseed` (the theta slider).
`l_delay` is fixed at soybean's value, so theta = l_reseed / l_delay.

NO LIVE IMD CALL
---------------
The prior is built from cached IMD rainfall + the cached, batch-parsed bulletin
text (D-15/D-16). `build_case()` asserts the bulletin cache exists rather than
fetching. There is no internet dependency at demo time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import build_labels
from src.features.seasonal_state import build_seasonal_table
from src.models.climatological_prior import (
    ClimatologicalPrior,
    RegimePrior,
    attach_seasonal_analog,
)
from src.models.decision_engine import CROP_DEFAULTS, CropEconomics, decide
from src.models.seasonal_analog_evidence import build_evidence

TARGET_DATE = "2018-07-15"
CROP = "soybean"
LABEL_YEARS = (2000, 2019)

# Exact evidence strings used in the Stage 4 worked example (D-20). The bulletin
# text is a fixed transcription of the cached ERF bulletin, not a fresh parse --
# the demo path does not re-run extraction.
_BULLETIN_EVIDENCE = (
    "IMD Extended Range bulletin places the monsoon trough north of its normal "
    "position in week 2, which IMD's glossary associates with a break in "
    "rainfall over central India."
)
_BULLETIN_SOURCE = "IMD ERF bulletin, week 2 (cached, batch-parsed - D-15/D-16)"

_BULLETIN_CACHE = "data/cache/bulletin_texts.json"


@dataclass(frozen=True)
class DemoCase:
    prior: RegimePrior
    l_delay: float                 # fixed; theta = l_reseed / l_delay
    l_reseed_default: float
    theta_default: float
    # The two structurally-different effective-N figures, kept separate.
    stage1_n_years: int             # climatology: independent seasons behind the base rate
    stage2_analog_effective_n: float  # analog: entropy-based size of the shown K=5 set
    stage2_analog_agreement: str

    def econ(self, l_reseed: float) -> CropEconomics:
        """A CropEconomics with the slider's l_reseed. verified stays False --
        the ICAR gap (D-20) does not close just because this is a demo."""
        base = CROP_DEFAULTS[CROP]
        return CropEconomics(
            crop=CROP,
            l_reseed=float(l_reseed),
            l_delay=self.l_delay,
            alpha=base.alpha,
            beta=base.beta,
            source=base.source,
            verified=False,
        )

    def decide_at(self, l_reseed: float):
        """Run the REAL decision engine at this l_reseed. Not a lookup table."""
        return decide(self.prior, self.econ(l_reseed))


def build_case() -> DemoCase:
    if not os.path.exists(_BULLETIN_CACHE):
        raise FileNotFoundError(
            f"{_BULLETIN_CACHE} missing. The demo consumes the cached bulletin "
            f"pipeline and will NOT fetch from internal.imd.gov.in. Run the "
            f"Stage 1/2 pipeline once to populate the cache."
        )

    rain = load_mcz_rainfall(*LABEL_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    prior = ClimatologicalPrior().fit(lab.labels).prior_for(
        TARGET_DATE,
        advisory_evidence=_BULLETIN_EVIDENCE,
        evidence_source=_BULLETIN_SOURCE,
    )
    st = build_seasonal_table(LABEL_YEARS).frame
    prior = attach_seasonal_analog(prior, build_evidence(st, 2018))

    base = CROP_DEFAULTS[CROP]
    return DemoCase(
        prior=prior,
        l_delay=base.l_delay,
        l_reseed_default=base.l_reseed,
        theta_default=base.l_reseed / base.l_delay,
        stage1_n_years=prior.effective_n,
        stage2_analog_effective_n=float(prior.seasonal_analog_effective_n),
        stage2_analog_agreement=str(prior.seasonal_analog_agreement),
    )

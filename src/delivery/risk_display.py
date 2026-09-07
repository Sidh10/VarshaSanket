"""Risk display -- a SINGLE regional indicator, deliberately not a choropleth.

WHAT STAGE 1 ACTUALLY COMPUTES
-----------------------------
`RegimePrior` is an MCZ-mean base rate: one probability triple for the whole
monsoon core zone (18-28N, 66.5-88E, 2684 IMD 0.25-deg cells;
src/data/imd_rainfall.py). There is NO per-block or per-village number in the
pipeline. D-16 further showed the sub-division reconciliation is coarse and the
one usable signal (trough position) is regional at best.

So this module renders ONE indicator for the whole pilot area. If it draws a
map, the pilot area is a SINGLE UNIFORM FILL -- there is no spatial variation in
the underlying numbers to colour. The "not resolved to blocks" caveat is baked
into both the text card and the SVG image itself, so a judge skimming the map
cannot come away thinking it is block-resolved.

ARCHITECTURE.md's "block-level choropleth" line in the output layer is
ASPIRATIONAL and is flagged as such (TASKS.md / D-21) -- it presumes a
block-resolved forecast the pipeline does not produce.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.delivery.advisory import SCALE_LABEL_EN
from src.models.decision_engine import DecisionResult

# MCZ bounding box, matching src/features/mcz.py (Rajeevan et al. 2010).
MCZ_LAT = (18.0, 28.0)
MCZ_LON = (65.0, 88.0)

# Colour by P(break). Bands are presentational only; the number is what matters.
_BANDS = [
    (0.00, 0.08, "#2e7d32", "low"),       # green
    (0.08, 0.15, "#f9a825", "moderate"),  # amber
    (0.15, 1.01, "#c62828", "elevated"),  # red
]


def _band(p_break: float) -> tuple[str, str]:
    for lo, hi, colour, label in _BANDS:
        if lo <= p_break < hi:
            return colour, label
    return "#9e9e9e", "unknown"


@dataclass(frozen=True)
class RegionalRiskIndicator:
    target_date: str
    crop: str
    p_active: float
    p_break: float
    p_transition: float
    recommendation: str
    robust: bool
    risk_colour: str
    risk_label: str
    scale_caveat: str
    disclosure_needed: bool

    def as_card_text(self) -> str:
        weak = "" if self.robust else "  (close call - weak)"
        disc = (
            "\n  NOTE: cost figures illustrative, not verified local prices (D-20)."
            if self.disclosure_needed
            else ""
        )
        return (
            f"MONSOON CORE ZONE - break-spell risk indicator\n"
            f"  date {self.target_date}   crop {self.crop}\n"
            f"  P(active) {self.p_active:.0%}   P(break) {self.p_break:.0%}   "
            f"P(transition) {self.p_transition:.0%}\n"
            f"  risk: {self.risk_label.upper()} ({self.risk_colour})   "
            f"recommendation: {self.recommendation.upper()}{weak}\n"
            f"  {self.scale_caveat}{disc}"
        )

    def as_uniform_svg(self, width: int = 420, height: int = 300) -> str:
        """One rectangle, one colour, caveat baked in. Not a choropleth."""
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  <rect x="20" y="20" width="{width-40}" height="150" fill="{self.risk_colour}" stroke="#333" stroke-width="1"/>
  <text x="{width/2}" y="95" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#fff" font-weight="bold">
    Break-spell risk: {self.risk_label.upper()}
  </text>
  <text x="{width/2}" y="120" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#fff">
    P(break) = {self.p_break:.0%}  |  {self.recommendation.upper()}
  </text>
  <text x="20" y="195" font-family="sans-serif" font-size="12" fill="#333" font-weight="bold">
    Whole monsoon core zone shown as one colour by design:
  </text>
  <text x="20" y="213" font-family="sans-serif" font-size="12" fill="#333">
    regional estimate, NOT resolved to individual blocks or villages.
  </text>
  <text x="20" y="235" font-family="sans-serif" font-size="11" fill="#777">
    MCZ box {MCZ_LAT[0]}-{MCZ_LAT[1]}N, {MCZ_LON[0]}-{MCZ_LON[1]}E  (Rajeevan et al. 2010)
  </text>
  <text x="20" y="252" font-family="sans-serif" font-size="11" fill="#777">
    {self.target_date}  |  crop: {self.crop}  |  climatological base rate, not a forecast
  </text>
  {"<text x='20' y='274' font-family='sans-serif' font-size='11' fill='#c62828'>NOTE: cost figures illustrative, not verified local prices (D-20).</text>" if self.disclosure_needed else ""}
</svg>"""


def build_indicator(result: DecisionResult) -> RegionalRiskIndicator:
    colour, label = _band(result.probabilities["break"])
    return RegionalRiskIndicator(
        target_date=result.target_date,
        crop=result.crop,
        p_active=result.probabilities["active"],
        p_break=result.probabilities["break"],
        p_transition=result.probabilities["transition"],
        recommendation=result.recommendation,
        robust=result.robust,
        risk_colour=colour,
        risk_label=label,
        scale_caveat=SCALE_LABEL_EN,
        disclosure_needed=bool(result.uses_unverified_parameters),
    )

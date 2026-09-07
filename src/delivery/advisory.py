"""Farmer-facing advisory generation.

WHICH LANGUAGE? -- the docs do not say, and this module does not guess
---------------------------------------------------------------------
Every reference to language in the repo is generic:

  ARCHITECTURE.md : "short *regional-language* message"
  README.md       : "delivered to the farmer's phone in *their own language*"
  AGENTS.md       : "Regional language output must be reviewable by someone who
                     reads that language before demo"
  CLAUDE.md       : GKMS is "vernacular" (describing a competitor, not a spec)

**No specific language (Hindi, Marathi, Telugu, ...) is named anywhere.** So:

  * `en` is the DEFAULT and the only rendering treated as verified. It is what
    `WhatsAppSender` sends unless explicitly overridden.
  * `hi` (Hindi) is provided as a WORKED STUB. It is the single most defensible
    choice for the MCZ -- Hindi-belt sub-divisions (MP x2, Rajasthan x2, UP x2,
    Bihar, Chhattisgarh, Jharkhand) are the plurality of the 18 MCZ-relevant
    sub-divisions (D-19). But it is **machine-generated and unreviewed**, every
    `hi` render carries an UNVERIFIED banner, and AGENTS.md's "reviewable by
    someone who reads that language before demo" is an OPEN blocking task
    (TASKS.md / D-21).
  * The frame is FULLY TEMPLATED per language -- fixed strings with slot
    substitution, no per-instance free translation -- so a reviewer checks a
    handful of templates, not every output.

EVIDENCE COMES THROUGH THE D-19 BOUNDARY, NOWHERE ELSE
-----------------------------------------------------
`render()` calls `advisory_evidence_lines(prior)` directly and asserts the
result equals `DecisionResult.evidence_lines` (which Stage 4 also sourced from
that same function). The raw `advisory_evidence` / `seasonal_analog_*` fields are
never read here. `_assert_boundary_respected()` enforces it.

THE ICAR GAP IS A FARMER'S PROBLEM
---------------------------------
When `result.uses_unverified_parameters` is True the disclosure appears in the
FARMER-FACING text, not only the technical view -- a short plain-language line,
not the long technical string. D-20: the cost figures are illustrative and
untraced; a farmer must not act on the rupee amounts as if they were real local
prices.

NO DATA ACQUISITION HERE
-----------------------
This module consumes a fully-built `RegimePrior` and `DecisionResult`. It does
not fetch anything. The trough evidence inside the prior came from the cached,
batch-parsed bulletin pipeline (D-15/D-16); there is no live call to
internal.imd.gov.in in the delivery path.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.models.climatological_prior import RegimePrior, advisory_evidence_lines
from src.models.decision_engine import DecisionResult

SUPPORTED_LANGUAGES = ("en", "hi")
DEFAULT_LANGUAGE = "en"
VERIFIED_LANGUAGES = ("en",)  # everything else renders with an UNVERIFIED banner

# Region label -- Stage 1 computes an MCZ-mean base rate (18-28N, 66.5-88E,
# 2684 cells; src/data/imd_rainfall.py). It is NOT block- or village-resolved.
# This string is repeated into every advisory and the risk display.
SCALE_LABEL_EN = (
    "Regional estimate for the monsoon core zone (central India). "
    "Not resolved to individual blocks or villages."
)
SCALE_LABEL_HI = (
    "[UNVERIFIED HINDI] मानसून कोर ज़ोन (मध्य भारत) के लिए क्षेत्रीय अनुमान। "
    "अलग-अलग ब्लॉक या गाँव के लिए नहीं।"
)


@dataclass(frozen=True)
class Advisory:
    language: str
    verified_language: bool
    recommendation: str            # "sow" | "wait"
    robust: bool
    p_break: float
    e_loss_sow: float
    e_loss_wait: float
    margin: float
    evidence_lines: tuple[str, ...]
    disclosure_shown: bool
    text: str                      # the full farmer-facing message
    char_count: int

    def describe(self) -> str:
        v = "verified" if self.verified_language else "UNVERIFIED - needs native review"
        return (
            f"Advisory [{self.language}, {v}]  {self.char_count} chars\n"
            f"  recommendation={self.recommendation}  robust={self.robust}  "
            f"disclosure_shown={self.disclosure_shown}\n"
            f"--- message ---\n{self.text}\n--- end ---"
        )


# ---------------------------------------------------------------------------
# Templates. One dict per language. Slots are filled by str.format.
# Keep these SHORT -- this is a WhatsApp message a farmer reads on a phone.
# ---------------------------------------------------------------------------

_T = {
    "en": {
        "header": "VarshaSanket advisory - {date} - {crop}",
        "sow": "Recommendation: SOW now. Conditions favour sowing.",
        "wait": "Recommendation: WAIT. Sowing now carries the higher risk.",
        "weak": " (This is a close call - it can change within the uncertainty range. Treat it as weak.)",
        "prob": "Chance of a dry break spell around this date: {p_break:.0f}%. Based on 20-year averages for this date, not a forecast for this year.",
        "loss": "Expected loss if you sow now: about Rs {e_sow:,.0f}/ha. If you wait: about Rs {e_wait:,.0f}/ha.",
        "evidence_head": "Supporting information:",
        "evidence_none": "- No extra evidence available for this date.",
        "scale": SCALE_LABEL_EN,
        "disclosure": (
            "IMPORTANT: the rupee figures above are illustrative examples, not "
            "verified local prices. Check current input and reseeding costs with "
            "your Krishi Vigyan Kendra before deciding."
        ),
    },
    # ---- UNVERIFIED machine translation. Reviewer: check every line. ----
    "hi": {
        "header": "[अनवेरिफाइड] वर्षासंकेत सलाह - {date} - {crop}",
        "sow": "सिफारिश: अभी बुवाई करें। परिस्थितियाँ बुवाई के अनुकूल हैं।",
        "wait": "सिफारिश: प्रतीक्षा करें। अभी बुवाई करने में अधिक जोखिम है।",
        "weak": " (यह निर्णय अनिश्चित है - अनिश्चितता की सीमा में बदल सकता है। इसे कमज़ोर मानें।)",
        "prob": "इस तिथि के आसपास सूखे 'ब्रेक' की संभावना: {p_break:.0f}%। यह इस तिथि के 20 साल के औसत पर आधारित है, इस साल का पूर्वानुमान नहीं।",
        "loss": "अभी बुवाई करने पर अनुमानित हानि: लगभग रु {e_sow:,.0f}/हेक्टेयर। प्रतीक्षा करने पर: लगभग रु {e_wait:,.0f}/हेक्टेयर।",
        "evidence_head": "सहायक जानकारी:",
        "evidence_none": "- इस तिथि के लिए अतिरिक्त जानकारी उपलब्ध नहीं।",
        "scale": SCALE_LABEL_HI,
        "disclosure": (
            "महत्वपूर्ण: ऊपर दिए गए रुपये के आंकड़े केवल उदाहरण हैं, सत्यापित स्थानीय "
            "कीमतें नहीं। निर्णय लेने से पहले अपने कृषि विज्ञान केंद्र से लागत की पुष्टि करें।"
        ),
        "unverified_banner": (
            "*** मशीन अनुवाद - समीक्षा नहीं हुई / MACHINE TRANSLATION, NOT REVIEWED ***"
        ),
    },
}


def _assert_boundary_respected(prior: RegimePrior, result: DecisionResult) -> None:
    """The evidence Stage 4 carried must be exactly what the D-19 boundary yields.

    If these differ, something bypassed `advisory_evidence_lines` upstream and
    the divided-case suppression may not have been applied.
    """
    boundary = tuple(advisory_evidence_lines(prior))
    if boundary != tuple(result.evidence_lines):
        raise ValueError(
            "D-19 boundary mismatch: advisory_evidence_lines(prior) != "
            f"result.evidence_lines\n  boundary : {boundary}\n  result   : {result.evidence_lines}"
        )


def render(
    result: DecisionResult,
    prior: RegimePrior,
    language: str = DEFAULT_LANGUAGE,
) -> Advisory:
    """Build the farmer-facing advisory for one decision, in one language."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language {language!r} not in {SUPPORTED_LANGUAGES}")
    _assert_boundary_respected(prior, result)

    t = _T[language]
    # >>> D-19 BOUNDARY: evidence text ONLY via advisory_evidence_lines <<<
    evidence = tuple(advisory_evidence_lines(prior))

    parts: list[str] = []
    if language not in VERIFIED_LANGUAGES and "unverified_banner" in t:
        parts.append(t["unverified_banner"])

    parts.append(t["header"].format(date=result.target_date, crop=result.crop))

    rec_line = t[result.recommendation]
    if not result.robust:
        rec_line += t["weak"]
    parts.append(rec_line)

    parts.append(t["prob"].format(p_break=100.0 * result.probabilities["break"]))
    parts.append(
        t["loss"].format(e_sow=result.e_loss_sow, e_wait=result.e_loss_wait)
    )

    parts.append(t["evidence_head"])
    if evidence:
        parts.extend(f"- {line}" for line in evidence)
    else:
        parts.append(t["evidence_none"])

    parts.append(t["scale"])

    disclosure_shown = bool(result.uses_unverified_parameters)
    if disclosure_shown:
        parts.append(t["disclosure"])

    text = "\n".join(parts)
    return Advisory(
        language=language,
        verified_language=language in VERIFIED_LANGUAGES,
        recommendation=result.recommendation,
        robust=result.robust,
        p_break=result.probabilities["break"],
        e_loss_sow=result.e_loss_sow,
        e_loss_wait=result.e_loss_wait,
        margin=result.margin,
        evidence_lines=evidence,
        disclosure_shown=disclosure_shown,
        text=text,
        char_count=len(text),
    )


def render_all(result: DecisionResult, prior: RegimePrior) -> dict[str, Advisory]:
    """Every supported language, for the technical/demo view."""
    return {lang: render(result, prior, lang) for lang in SUPPORTED_LANGUAGES}

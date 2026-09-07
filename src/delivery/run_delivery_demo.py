"""End-to-end delivery demo for the 2018-07-15 soybean case used in Stage 4.

Usage:  python -m src.delivery.run_delivery_demo

Rebuilds the exact Stage 4 worked example (D-20), then renders the advisory,
does a WhatsApp dry-run, and builds the regional risk indicator + SVG.

No data acquisition: the trough evidence is read from the cached bulletin
pipeline. If the cache is missing this errors rather than fetching -- there is
no live internal.imd.gov.in call in the delivery path.
"""

from __future__ import annotations

import ast
import inspect
import os

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import build_labels
from src.features.seasonal_state import build_seasonal_table
from src.models.climatological_prior import ClimatologicalPrior, attach_seasonal_analog
from src.models.decision_engine import CROP_DEFAULTS, decide
from src.models.seasonal_analog_evidence import build_evidence

from src.delivery import advisory as advisory_mod
from src.delivery.advisory import render, render_all
from src.delivery.risk_display import build_indicator
from src.delivery.whatsapp import SANDBOX_JOIN_HELP, WhatsAppSender

LABEL_YEARS = (2000, 2019)
ARTIFACT = "artifacts/delivery_demo_2018.txt"
SVG_ARTIFACT = "artifacts/delivery_risk_indicator_2018.svg"


def _check_no_raw_evidence_access() -> None:
    """AST check: the delivery advisory module reads evidence only via the boundary."""
    tree = ast.parse(inspect.getsource(advisory_mod))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    raw = {"advisory_evidence", "evidence_source", "seasonal_analog_evidence",
           "seasonal_analog_years", "seasonal_analog_detail",
           "seasonal_analog_effective_n", "seasonal_analog_agreement"}
    leaked = sorted(raw & attrs)
    print("D-19 BOUNDARY CHECK (src/delivery/advisory.py)")
    print(f"  imports advisory_evidence_lines: {'advisory_evidence_lines' in imported}")
    print(f"  raw evidence fields read directly: {leaked or 'NONE'}")
    assert "advisory_evidence_lines" in imported
    assert not leaked
    # And no live IMD fetch in EXECUTABLE code. Strip docstrings first -- the
    # module docstring mentions internal.imd.gov.in as prose (same
    # prose-vs-code false positive already hit on 'week' and 'C/L').
    for n in ast.walk(tree):
        if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef) and ast.get_docstring(n):
            n.body = n.body[1:]
    code_only = ast.unparse(tree)
    live_refs = [h for h in ("internal.imd.gov.in", "requests.get", "urlopen", "httpx")
                 if h in code_only]
    print(f"  live-fetch tokens in EXECUTABLE code: {live_refs or 'NONE'}")
    assert not live_refs
    print()


def _no_live_fetch_check() -> None:
    """The delivery demo must consume the bulletin cache, not trigger a download."""
    cache = "data/cache/bulletin_texts.json"
    print("NO-LIVE-FETCH CHECK")
    print(f"  bulletin cache present: {os.path.exists(cache)}  ({cache})")
    assert os.path.exists(cache), (
        "bulletin cache missing -- run the Stage 1/2 pipeline first. The delivery "
        "demo will NOT fetch from internal.imd.gov.in."
    )
    print("  delivery demo reads cache only; no live IMD call.\n")


def build_prior_and_result():
    rain = load_mcz_rainfall(*LABEL_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    prior_model = ClimatologicalPrior().fit(lab.labels)
    st = build_seasonal_table(LABEL_YEARS).frame

    # Same inputs as src/models/run_stage4_decision.py
    prior = prior_model.prior_for(
        "2018-07-15",
        advisory_evidence=(
            "IMD Extended Range bulletin places the monsoon trough north of its "
            "normal position in week 2, which IMD's glossary associates with a "
            "break in rainfall over central India."
        ),
        evidence_source="IMD ERF bulletin, week 2 (cached, batch-parsed - D-15/D-16)",
    )
    prior = attach_seasonal_analog(prior, build_evidence(st, 2018))
    result = decide(prior, CROP_DEFAULTS["soybean"])
    return prior, result


def main() -> None:
    lines: list[str] = []

    def out(s: str = "") -> None:
        print(s)
        lines.append(s)

    _check_no_raw_evidence_access()
    _no_live_fetch_check()

    prior, result = build_prior_and_result()

    out("=" * 78)
    out("DELIVERY DEMO -- 2018-07-15, soybean  (same case as Stage 4 / D-20)")
    out("=" * 78)
    out(f"  recommendation : {result.recommendation.upper()}")
    out(f"  E[loss|SOW]  = {result.e_loss_sow:,.0f} INR/ha")
    out(f"  E[loss|WAIT] = {result.e_loss_wait:,.0f} INR/ha")
    out(f"  margin (E[wait]-E[sow]) = {result.margin:+,.0f}  robust={result.robust}")
    out(f"  uses_unverified_parameters = {result.uses_unverified_parameters}")
    out(f"  evidence_lines (via D-19 boundary): {len(result.evidence_lines)}")

    out("\n" + "=" * 78)
    out("LANGUAGE(S) SPECIFIED IN THE DOCS")
    out("=" * 78)
    out("  ARCHITECTURE.md : 'short regional-language message'   (no language named)")
    out("  README.md       : 'in their own language'            (no language named)")
    out("  AGENTS.md       : 'reviewable by someone who reads that language before demo'")
    out("  => NO specific language is specified anywhere. English is the verified")
    out("     default; Hindi is a machine-generated STUB pending native review (D-21).")

    advs = render_all(result, prior)
    for lang, adv in advs.items():
        out("\n" + "=" * 78)
        out(f"ADVISORY [{lang}]")
        out("=" * 78)
        out(adv.describe())

    out("\n" + "=" * 78)
    out("WHATSAPP -- Twilio Sandbox (dry run; no credentials, nothing sent)")
    out("=" * 78)
    out(SANDBOX_JOIN_HELP)
    sender = WhatsAppSender(dry_run=True)
    res_en = sender.send("+919000000000", advs["en"])
    out(res_en.describe())
    out("")
    try:
        sender.send("+919000000000", advs["hi"])
    except ValueError as e:
        out(f"  refused to send 'hi' by default: {e}")
    res_hi = sender.send("+919000000000", advs["hi"], allow_unverified_language=True)
    out("\n  (hi, internal testing only, allow_unverified_language=True):")
    out(res_hi.describe())

    out("\n" + "=" * 78)
    out("REGIONAL RISK INDICATOR -- one region, one colour, NOT a choropleth")
    out("=" * 78)
    ind = build_indicator(result)
    out(ind.as_card_text())
    svg = ind.as_uniform_svg()
    os.makedirs("artifacts", exist_ok=True)
    with open(SVG_ARTIFACT, "w", encoding="utf-8") as f:
        f.write(svg)
    out(f"\n  uniform-fill SVG written to {SVG_ARTIFACT}")
    out("  (single rectangle; 'not resolved to individual blocks' baked into the image)")

    with open(ARTIFACT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nwrote {ARTIFACT}")


if __name__ == "__main__":
    main()

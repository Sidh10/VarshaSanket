"""Stage 4 worked example, end to end. Usage: python -m src.models.run_stage4_decision"""

from __future__ import annotations

import ast
import inspect

import pandas as pd

from src.data.imd_rainfall import load_mcz_rainfall
from src.features.labels import build_labels
from src.features.seasonal_state import build_seasonal_table
from src.models import decision_engine as de
from src.models.climatological_prior import ClimatologicalPrior, attach_seasonal_analog
from src.models.decision_engine import CROP_DEFAULTS, advisory_text, decide
from src.models.seasonal_analog_evidence import build_evidence

LABEL_YEARS = (2000, 2019)


def check_d19_boundary() -> None:
    """Verify by INSPECTION that Stage 4 reads evidence only via the boundary.

    Checks the actual import and call, and that no raw evidence field is
    touched anywhere in decision_engine -- not that the interface 'was
    followed'.
    """
    print("=" * 78)
    print("D-19 BOUNDARY CHECK (by inspection of decision_engine source)")
    print("=" * 78)
    src = inspect.getsource(de)
    tree = ast.parse(src)

    imported = {
        a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
        for a in n.names
    }
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute | ast.Name)
        and isinstance(n.func, ast.Name)
    }
    # attribute reads on the prior, e.g. prior.advisory_evidence
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
    assert "advisory_evidence_lines" in imported, "boundary function not imported"
    assert "advisory_evidence_lines" in called, "boundary function never called"
    assert not leaked, f"Stage 4 reads raw evidence fields directly: {leaked}"
    print("  -> Stage 4 obtains farmer-facing evidence ONLY via the D-19 boundary.\n")


def check_no_threshold_rule() -> None:
    """Structural check that no `P > C/L`-shaped comparison exists."""
    print("=" * 78)
    print("D-C GUARD CHECK (no cost-loss threshold anywhere)")
    print("=" * 78)
    src = inspect.getsource(de)
    # Scan EXECUTABLE code only. The module docstring deliberately contains the
    # string "P > C/L" to explain what must not be done; a raw substring scan
    # flags that as a violation, which is a false positive of the same kind
    # already hit on 'week' in the analog module.
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Module | ast.ClassDef | ast.FunctionDef) and ast.get_docstring(n):
            n.body = n.body[1:]
    code_only = ast.unparse(tree)
    banned = [t for t in ("C/L", "cost_loss", "threshold_rule") if t in code_only]
    in_prose = [t for t in ("C/L", "cost_loss", "threshold_rule") if t in src and t not in code_only]
    print(f"  banned tokens in EXECUTABLE code: {banned or 'NONE'}")
    print(f"  (same tokens appearing only in prose/docstrings: {in_prose or 'none'})")
    assert not banned, f"cost-loss threshold construct found in code: {banned}"

    # Both branches must be scored by the same expectation function.
    calls = [
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "_expected_loss"
    ]
    print(f"  _expected_loss call sites       : {len(calls)} (both branches + envelope)")
    assert len(calls) >= 2, "both branches must go through _expected_loss"

    # The guard must actually reject a flat branch.
    import numpy as np
    try:
        de._expected_loss(np.array([0.1, 0.2, 0.7]), np.array([5.0, 5.0, 5.0]), "test")
        raise SystemExit("GUARD FAILED: a constant loss vector was accepted")
    except ValueError as e:
        print(f"  guard rejects a flat branch     : YES")
        print(f"    -> {str(e)[:96]}...")
    # And must reject a non-distribution.
    try:
        de._expected_loss(np.array([0.5]), np.array([1.0]), "test")
        raise SystemExit("GUARD FAILED: a single probability was accepted")
    except ValueError as e:
        print(f"  guard rejects a single P        : YES")
        print(f"    -> {str(e)[:96]}...\n")


def main() -> None:
    check_d19_boundary()
    check_no_threshold_rule()

    rain = load_mcz_rainfall(*LABEL_YEARS)
    lab = build_labels(rain.series, months=(6, 9))
    prior_model = ClimatologicalPrior().fit(lab.labels)
    st = build_seasonal_table(LABEL_YEARS).frame

    # 2018 is the only 'leaning' year, so its analog evidence IS farmer-facing.
    target = "2018-07-15"
    prior = prior_model.prior_for(
        target,
        advisory_evidence=(
            "IMD Extended Range bulletin places the monsoon trough north of its "
            "normal position in week 2, which IMD's glossary associates with a "
            "break in rainfall over central India."
        ),
        evidence_source="IMD ERF bulletin, week 2",
    )
    prior = attach_seasonal_analog(prior, build_evidence(st, 2018))

    print("=" * 78)
    print("STAGE 1 INPUT")
    print("=" * 78)
    print(prior.describe())

    econ = CROP_DEFAULTS["soybean"]
    print("\n" + "=" * 78)
    print(f"CROP INPUTS -- {econ.crop}")
    print("=" * 78)
    print(f"  L_reseed = {econ.l_reseed:,.0f} INR/ha   (sown, then a break spell)")
    print(f"  L_delay  = {econ.l_delay:,.0f} INR/ha   (waited, but rains came)")
    print(f"  alpha    = {econ.alpha}  (share of L_reseed in a transition window)")
    print(f"  beta     = {econ.beta}  (share of L_delay in a transition window)")
    print(f"  theta    = {econ.theta:.3f}")
    print(f"  verified = {econ.verified}")

    res = decide(prior, econ)
    print("\n" + "=" * 78)
    print("WORKED EXAMPLE -- both branches shown term by term")
    print("=" * 78)
    print(res.worked_example())

    print("\n" + "=" * 78)
    print("FARMER-FACING ADVISORY")
    print("=" * 78)
    print(advisory_text(res))

    # theta sensitivity: show the flip, without ever using a threshold rule.
    print("\n" + "=" * 78)
    print("theta SENSITIVITY (both branches re-expected at each theta; no threshold)")
    print("=" * 78)
    print(f"  {'L_reseed':>9} {'theta':>7} {'E[sow]':>10} {'E[wait]':>10} {'decision':>9}")
    for lr in (6000, 9000, 12000, 15000, 18000, 24000):
        e2 = de.CropEconomics(crop="soybean", l_reseed=float(lr), l_delay=econ.l_delay,
                              source=econ.source, verified=False)
        r2 = decide(prior, e2)
        print(f"  {lr:>9,} {r2.theta:>7.2f} {r2.e_loss_sow:>10,.0f} "
              f"{r2.e_loss_wait:>10,.0f} {r2.recommendation.upper():>9}")

    print("\n" + "=" * 78)
    print("ICAR CITATION STATUS: **STILL OPEN** -- see DISCUSSION D-20 / RESEARCH.md.")
    print("No ICAR threshold is hardcoded. Monetary values are illustrative.")
    print("=" * 78)


if __name__ == "__main__":
    main()

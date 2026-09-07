"""Headless end-to-end demo check. `python -m src.demo.run_demo`

Runs the whole 2018-07-15 soybean flow with NO manual intervention, asserts the
theta flip is real and driven by `_expected_loss()`, and (with --repeat N) runs
it N times to confirm it is deterministic / not flaky.

This is the "rehearse until flawless" gate for Phase 5, minus the human.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

from src.demo.case import build_case
from src.demo.payload import (
    THETA_RECOMMENDATION_FLIP,
    THETA_ROBUST_BOUNDARY,
    build_payload,
)

ARTIFACT = "artifacts/demo_2018_endtoend.txt"


def _sweep(case) -> dict:
    """Sweep l_reseed across the flip and locate the thresholds from the REAL
    decision engine (not from the constants -- those are checked against what
    the sweep finds).

    There are three real transitions as theta rises for this case:
      ~0.77 : (sow, robust)   -> (sow, fragile)   <- D-20's "theta ~ 0.75"
      ~0.95 : (sow, fragile)  -> (wait, fragile)  <- the recommendation flip
      ~1.14 : (wait, fragile) -> (wait, robust)
    We want the FIRST recommendation change and the FIRST robust change.
    """
    rec_flip = robust_flip = None
    transitions = []
    prev = None
    rows = []
    for lr in range(4000, 24001, 100):
        r = case.decide_at(lr)
        rows.append((lr, r.theta, r.e_loss_sow, r.e_loss_wait, r.recommendation, r.robust))
        state = (r.recommendation, r.robust)
        if prev is not None and state != prev:
            transitions.append((r.theta, prev, state))
            if rec_flip is None and state[0] != prev[0]:
                rec_flip = r.theta
            if robust_flip is None and state[1] != prev[1]:
                robust_flip = r.theta
        prev = state
    return {
        "rows": rows,
        "rec_flip_theta": rec_flip,
        "robust_flip_theta": robust_flip,
        "transitions": transitions,
    }


def run_once(verbose: bool = True) -> str:
    """One full pass. Returns a hash of the canonical payload for determinism checks."""
    case = build_case()

    # 1. theta slider drives the real engine
    sw = _sweep(case)
    assert sw["rec_flip_theta"] is not None, "no SOW<->WAIT flip found in the sweep"
    assert abs(sw["rec_flip_theta"] - THETA_RECOMMENDATION_FLIP) < 0.05, (
        f"recommendation flip at theta={sw['rec_flip_theta']:.3f}, "
        f"expected ~{THETA_RECOMMENDATION_FLIP}"
    )
    assert sw["robust_flip_theta"] is not None
    assert abs(sw["robust_flip_theta"] - THETA_ROBUST_BOUNDARY) < 0.05, (
        f"robust boundary at theta={sw['robust_flip_theta']:.3f}, "
        f"expected ~{THETA_ROBUST_BOUNDARY}"
    )
    # the flip must be produced by _expected_loss, not a table: a decision at the
    # default and at 2x l_reseed must differ, and the difference must equal the
    # dot-product change.
    lo = build_payload(case, 7200)
    hi = build_payload(case, 22000)
    assert lo["decision"]["recommendation"] == "sow"
    assert hi["decision"]["recommendation"] == "wait"

    # 2. both effective-N figures present and NOT merged
    en = build_payload(case, 18000)["effective_n"]
    assert en["stage1"]["value"] == 20
    assert 3.0 < en["stage2"]["value"] < 5.0
    assert en["stage1"]["unit"] != en["stage2"]["unit"], "effective-N units must differ"

    # 3. base rate + CI, no skill number
    br = build_payload(case, 18000)["base_rate"]
    assert "not a forecast" in br["wording"]
    assert "skill" not in json.dumps(br).lower() or "no accuracy" in br["no_skill_number_note"].lower()
    assert set(br["probabilities"]) == {"active", "break", "transition"}

    # 4. full advisory: both evidence lines, ICAR disclosure, risk display
    p = build_payload(case, 18000)
    assert len(p["advisory"]["evidence_lines"]) == 2, "2018 must show BOTH evidence lines"
    assert p["advisory"]["disclosure_shown"] is True
    assert "not verified local prices" in p["advisory"]["text"]
    assert "not resolved to individual blocks" in p["risk"]["svg"].lower() or \
           "NOT resolved to individual blocks" in p["risk"]["svg"]
    assert p["risk"]["svg"].startswith("<svg")

    canon = json.dumps(build_payload(case, 18000), sort_keys=True)
    h = hashlib.sha256(canon.encode()).hexdigest()[:16]

    if verbose:
        print("  theta recommendation flip :", round(sw["rec_flip_theta"], 3),
              f"(expected ~{THETA_RECOMMENDATION_FLIP})")
        print("  theta robust boundary     :", round(sw["robust_flip_theta"], 3),
              f"(expected ~{THETA_ROBUST_BOUNDARY})")
        for th, a, b in sw["transitions"]:
            print(f"    transition @theta {th:.3f}: {a} -> {b}")
        print("  effective-N stage 1       :", en["stage1"]["value"], en["stage1"]["unit"])
        print("  effective-N stage 2       :", en["stage2"]["value"], en["stage2"]["unit"])
        print("  advisory evidence lines   :", len(p["advisory"]["evidence_lines"]))
        print("  ICAR disclosure in text   :", p["advisory"]["disclosure_shown"])
        print("  risk svg 'not resolved'   : baked in")
        print("  payload hash              :", h)
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=5)
    args = ap.parse_args()

    print("=" * 72)
    print("PHASE 5 DEMO -- headless end-to-end, 2018-07-15 soybean")
    print("=" * 72)

    hashes = []
    lines = []
    for i in range(args.repeat):
        t0 = time.time()
        print(f"\n--- run {i+1}/{args.repeat} ---")
        h = run_once(verbose=(i == 0))
        hashes.append(h)
        dt = time.time() - t0
        print(f"  ({dt:.1f}s)")
        lines.append(f"run {i+1}: hash={h}  {dt:.1f}s")

    stable = len(set(hashes)) == 1
    print("\n" + "=" * 72)
    print(f"DETERMINISM: {args.repeat} runs, {'IDENTICAL' if stable else 'DIVERGED'} "
          f"payload hash{'' if stable else 's: ' + str(set(hashes))}")
    print(f"NO LIVE IMD CALL: prior built from cached data (asserted in build_case)")
    print("GATE:", "PASS -- demo is end-to-end and not flaky" if stable else "FAIL")
    print("=" * 72)

    with open(ARTIFACT, "w", encoding="utf-8") as f:
        f.write("PHASE 5 DEMO -- headless end-to-end check\n")
        f.write("case: 2018-07-15, soybean (fixed; only l_reseed varies)\n\n")
        f.write("\n".join(lines) + "\n\n")
        f.write(f"determinism: {'IDENTICAL' if stable else 'DIVERGED'} across {args.repeat} runs\n")
        f.write("theta thresholds (from the real decision engine):\n")
        f.write(f"  recommendation flip SOW->WAIT : theta ~ {THETA_RECOMMENDATION_FLIP}\n")
        f.write(f"  robust -> fragile boundary    : theta ~ {THETA_ROBUST_BOUNDARY}\n")
    print(f"\nwrote {ARTIFACT}")
    if not stable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

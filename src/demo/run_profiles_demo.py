"""Headless end-to-end check for the per-farmer profile screen.
`python -m src.demo.run_profiles_demo`

Same "rehearse until flawless" standard as `run_demo.py` (Phase 5): runs all
four demo profiles with NO manual intervention, asserts the properties the
UI depends on, and (with --repeat N) repeats N times to confirm the payloads
are deterministic / not flaky.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

from src.demo.case import build_case
from src.demo.profiles import DEMO_PROFILES, build_profile_payload

ARTIFACT = "artifacts/demo_profiles_endtoend.txt"

# Expected shape, asserted against the REAL pipeline output every run -- not
# hardcoded numbers standing in for it. A/B/C are pre-sowing (decision != None);
# D is sown (decision is None).
_EXPECT_RECOMMENDATION = {"A": "sow", "B": "wait", "C": "wait"}
_EXPECT_ROBUST = {"A": False, "B": True, "C": False}


def run_once(verbose: bool = True) -> str:
    """One full pass over all four profiles. Returns a hash of the canonical
    combined payload for determinism checks."""
    case = build_case()
    payloads = {}

    for key, profile in DEMO_PROFILES.items():
        p = build_profile_payload(case, key)
        payloads[key] = p

        assert p["profile"]["is_illustrative"] is True, f"{key}: not marked illustrative"
        assert p["base_rate"]["probabilities"] == dict(case.prior.probabilities), (
            f"{key}: base rate diverged from the shared prior"
        )

        if key == "D":
            assert p["decision"] is None, "D (sown) must carry no SOW/WAIT decision"
            assert p["applicability"] == "post_sowing_contingency_not_modelled"
            assert p["not_modelled_reason"], "D must explain why, not fail silently"
            continue

        assert p["decision"] is not None, f"{key}: expected a decision, got None"
        d = p["decision"]
        assert d["recommendation"] == _EXPECT_RECOMMENDATION[key], (
            f"{key}: recommendation {d['recommendation']!r}, "
            f"expected {_EXPECT_RECOMMENDATION[key]!r}"
        )
        assert d["robust"] == _EXPECT_ROBUST[key], (
            f"{key}: robust={d['robust']}, expected {_EXPECT_ROBUST[key]}"
        )
        # both branches probability-weighted -- the D-C property, re-checked here
        assert len(d["contributions"]["prob"]) == 3
        assert abs(sum(d["contributions"]["prob"]) - 1.0) < 1e-9

        # base vs effective economics both present and distinct where a
        # multiplier != 1.0 was applied
        econ = p["economics"]
        assert econ["base"]["l_reseed"] != econ["effective"]["l_reseed"] or (
            econ["multipliers"]["l_reseed"] == 1.0
        )

        # full advisory -- nothing simplified from Phase 4b
        adv = p["advisory"]
        assert len(adv["evidence_lines"]) == 2, f"{key}: expected both 2018 evidence lines"
        assert adv["disclosure_shown"] is True
        assert "not verified local prices" in adv["text"]
        assert p["risk"]["svg"].startswith("<svg")

    canon = json.dumps(payloads, sort_keys=True)
    h = hashlib.sha256(canon.encode()).hexdigest()[:16]

    if verbose:
        for key in DEMO_PROFILES:
            p = payloads[key]
            if p["decision"] is None:
                print(f"  {key}: {p['profile']['label']}")
                print(f"       -> NO DECISION ({p['applicability']})")
            else:
                d = p["decision"]
                print(f"  {key}: {p['profile']['label']}")
                print(f"       crop={p['profile']['crop']}  "
                      f"E[sow]={d['e_loss_sow']:,.0f}  E[wait]={d['e_loss_wait']:,.0f}  "
                      f"-> {d['recommendation'].upper()}  (robust={d['robust']})")
        print("  payload hash              :", h)
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=5)
    args = ap.parse_args()

    print("=" * 72)
    print("PER-FARMER PROFILE DEMO -- headless end-to-end, 2018-07-15, 4 profiles")
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
    print("NO LIVE IMD CALL: prior built from cached data (asserted in build_case)")
    print("GATE:", "PASS -- profile screen is end-to-end and not flaky" if stable else "FAIL")
    print("=" * 72)

    with open(ARTIFACT, "w", encoding="utf-8") as f:
        f.write("PER-FARMER PROFILE DEMO -- headless end-to-end check\n")
        f.write("case: 2018-07-15 (shared prior); profiles A/B/C/D, src/demo/profiles.py\n\n")
        f.write("\n".join(lines) + "\n\n")
        f.write(f"determinism: {'IDENTICAL' if stable else 'DIVERGED'} across {args.repeat} runs\n")
    print(f"\nwrote {ARTIFACT}")
    if not stable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

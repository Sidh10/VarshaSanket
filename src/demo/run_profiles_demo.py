"""Headless end-to-end sweep for the per-farmer profile screen.
`python -m src.demo.run_profiles_demo`

WHY A SWEEP AND NOT A REPEAT-THE-FIXED-CASES CHECK (D-28)
---------------------------------------------------------
While the screen offered four fixed profiles, the honest check was "run those
four repeatedly and confirm the payload never changes" (D-27). Free selection
makes that the wrong shape of test: the input space is now everything the
schema can express, so the question is no longer "is one case stable" but
"is EVERY reachable combination either scored or cleanly refused."

So this drives the **entire cartesian product** of the selectable fields --
crop x sowing status x irrigation x soil x risk x growth stage -- through the
**real HTTP endpoint** (a real server on a real socket, not the Python function
called directly), and classifies every response:

  scored            200 with a SOW/WAIT decision      (pre-sowing combinations)
  no-decision       200 with decision=null            (already-sown: a different
                                                       action set, not modelled)
  refused           400 with a plain-language reason  (combinations
                                                       FarmerProfile.__post_init__
                                                       rejects)
  FAILURE           anything else: a 500, a traceback in the body, a malformed
                    payload, or a validation message that is empty/technical

A single FAILURE fails the run. The point is that no input a person can select
-- or hand-type into the URL -- reaches the client as a stack trace.

The server is started IN-PROCESS on an ephemeral port (port 0), so this cannot
collide with a stale demo server on 8765 -- the exact hazard that cost a debug
cycle in D-27 and is now a pre-demo checklist line.
"""

from __future__ import annotations

import argparse
import itertools
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from src.demo.case import build_case
from src.demo.profiles import (
    DEMO_PROFILES,
    profile_option_values,
)

ARTIFACT = "artifacts/demo_profiles_endtoend.txt"

# The rehearsed presets must keep giving the rehearsed answer. Not a
# determinism harness -- a guard against a silent behaviour change in the
# shared decision path.
_EXPECT_RECOMMENDATION = {"A": "sow", "B": "wait", "C": "wait"}
_EXPECT_ROBUST = {"A": False, "B": True, "C": False}


# ---------------------------------------------------------------------------
# The real server, in-process, on an ephemeral port
# ---------------------------------------------------------------------------


def _start_server():
    """Boot the actual demo server with the case pre-built. Returns (base_url, srv)."""
    import src.demo.server as server_mod

    server_mod._CASE = build_case()  # one build, shared by every request below
    srv = server_mod._Server(("127.0.0.1", 0), server_mod.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}", srv


def _get(url: str) -> tuple[int, str]:
    """GET, returning (status, body) for error responses too rather than raising."""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def _decide_url(base: str, fields: dict[str, str]) -> str:
    return f"{base}/api/profile_decide?" + urllib.parse.urlencode(fields)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _classify(status: int, body: str) -> tuple[str, str]:
    """-> (outcome, detail). outcome in {scored, no-decision, refused, FAILURE}."""
    if "Traceback (most recent call last)" in body:
        return "FAILURE", "response body contains a Python traceback"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "FAILURE", f"body is not JSON (status {status})"

    if status == 200:
        if "decision" not in payload:
            return "FAILURE", "200 without a decision key"
        if payload["decision"] is None:
            if not payload.get("not_modelled_reason"):
                return "FAILURE", "no-decision response carries no reason"
            return "no-decision", payload["applicability"]
        rec = payload["decision"].get("recommendation")
        if rec not in ("sow", "wait"):
            return "FAILURE", f"unexpected recommendation {rec!r}"
        return "scored", rec

    if status == 400:
        if payload.get("kind") != "validation":
            return "FAILURE", f"400 not marked as a validation error: {payload!r}"
        msg = payload.get("error", "")
        if not msg or len(msg) < 20:
            return "FAILURE", f"validation message is empty or too terse: {msg!r}"
        # a plain-language reason, not an exception repr
        if "Error(" in msg or msg.startswith("Traceback"):
            return "FAILURE", f"validation message looks like a raw exception: {msg!r}"
        return "refused", msg

    return "FAILURE", f"unexpected status {status}: {body[:160]}"


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


def sweep(base: str, verbose: bool = True) -> dict:
    """Drive every combination the schema can express through the endpoint."""
    opts = profile_option_values()
    axes = {
        "crop": [o["value"] for o in opts["crop"]],
        "sowing_status": [o["value"] for o in opts["sowing_status"]],
        "irrigation": [o["value"] for o in opts["irrigation"]],
        "soil": [o["value"] for o in opts["soil"]],
        "risk": [o["value"] for o in opts["risk"]],
        # the FULL stage enum, including the value that is only coherent before
        # sowing -- so the invalid halves of the space are swept too
        "growth_stage": [o["value"] for o in opts["growth_stage"]],
    }
    names = list(axes)
    counts = {"scored": 0, "no-decision": 0, "refused": 0, "FAILURE": 0}
    failures: list[tuple[dict, str]] = []
    recommendations = {"sow": 0, "wait": 0}

    for combo in itertools.product(*(axes[n] for n in names)):
        fields = dict(zip(names, combo))
        status, body = _get(_decide_url(base, fields))
        outcome, detail = _classify(status, body)
        counts[outcome] += 1
        if outcome == "scored":
            recommendations[detail] += 1
        if outcome == "FAILURE":
            failures.append((fields, detail))

    total = sum(counts.values())
    if verbose:
        print(f"  combinations swept        : {total}")
        print(f"    scored (SOW/WAIT)       : {counts['scored']}"
              f"   [sow {recommendations['sow']} / wait {recommendations['wait']}]")
        print(f"    no-decision (sown)      : {counts['no-decision']}")
        print(f"    refused (clean 400)     : {counts['refused']}")
        print(f"    FAILURES                : {counts['FAILURE']}")
        for fields, why in failures[:10]:
            print(f"      ! {fields} -> {why}")
    return {"counts": counts, "total": total, "failures": failures,
            "recommendations": recommendations}


def check_presets(base: str, verbose: bool = True) -> list[str]:
    """The four presets still behave, and match their free-form equivalent.

    The convergence check is the one that matters architecturally: a preset and
    a hand-picked profile with the same fields must produce the same payload,
    or there are two decision paths on this screen.
    """
    problems = []
    for key, profile in DEMO_PROFILES.items():
        status, body = _get(f"{base}/api/profile_decide?profile={key}")
        if status != 200:
            problems.append(f"preset {key}: status {status}")
            continue
        preset = json.loads(body)

        if key in _EXPECT_RECOMMENDATION:
            d = preset.get("decision")
            if d is None:
                problems.append(f"preset {key}: expected a decision, got none")
            else:
                if d["recommendation"] != _EXPECT_RECOMMENDATION[key]:
                    problems.append(
                        f"preset {key}: recommendation {d['recommendation']}, "
                        f"expected {_EXPECT_RECOMMENDATION[key]}")
                if d["robust"] != _EXPECT_ROBUST[key]:
                    problems.append(
                        f"preset {key}: robust={d['robust']}, expected {_EXPECT_ROBUST[key]}")
                if len(preset["advisory"]["evidence_lines"]) != 2:
                    problems.append(f"preset {key}: expected both 2018 evidence lines")
                if not preset["advisory"]["disclosure_shown"]:
                    problems.append(f"preset {key}: ICAR disclosure not shown")
        elif preset.get("decision") is not None:
            problems.append(f"preset {key}: expected no decision (already sown)")

        # same fields, chosen freely -> must be the same payload
        fields = {
            "crop": profile.crop,
            "sowing_status": profile.sowing_status.value,
            "irrigation": profile.irrigation.value,
            "soil": profile.soil.value,
            "risk": profile.risk.value,
            "growth_stage": profile.growth_stage.value,
        }
        status, body = _get(_decide_url(base, fields))
        if status != 200:
            problems.append(f"preset {key}: free-form equivalent returned {status}")
            continue
        custom = json.loads(body)
        # everything but the `profile` block (which carries the key and the
        # preset's own prose label) must be identical
        a = {k: v for k, v in preset.items() if k != "profile"}
        b = {k: v for k, v in custom.items() if k != "profile"}
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            problems.append(f"preset {key}: preset and free-form payloads DIVERGE")
        elif verbose:
            print(f"    {key}: preset == free-form (same decision path)  OK")
    return problems


def check_no_schema_literals_in_page() -> list[str]:
    """The UI must not carry a hand-written copy of any schema value.

    If it does, the page can drift from `FarmerProfile` -- offering a value the
    schema no longer has, or missing one it gained. Options are served by
    `/api/profile_options` precisely so this stays true.
    """
    import src.demo.server as server_mod
    from src.models.decision_engine import CROP_DEFAULTS
    from src.models.farmer_profile import (
        GrowthStage,
        IrrigationAccess,
        RiskPreference,
        SoilType,
        SowingStatus,
    )

    values = set(list(CROP_DEFAULTS))
    for enum_cls in (SowingStatus, GrowthStage, IrrigationAccess, SoilType, RiskPreference):
        values.update(m.value for m in enum_cls)
    page = server_mod.PROFILES_PAGE
    leaked = sorted(v for v in values if f"'{v}'" in page or f'"{v}"' in page)
    return [f"profiles page hard-codes schema value(s): {leaked}"] if leaked else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1,
                    help="repeat the whole sweep N times (default 1)")
    args = ap.parse_args()

    print("=" * 72)
    print("PER-FARMER PROFILE SCREEN -- full combination sweep over real HTTP")
    print("=" * 72)
    print("Building the demo case (cached data, no live IMD call)...")
    t0 = time.time()
    base, srv = _start_server()
    print(f"  server up on {base}  ({time.time()-t0:.1f}s)\n")

    all_problems: list[str] = []
    results = []
    try:
        lit = check_no_schema_literals_in_page()
        print("--- UI holds no hand-written schema values ---")
        print("  " + (lit[0] if lit else "confirmed: options come from the schema only"))
        all_problems += lit

        for i in range(args.repeat):
            print(f"\n--- sweep {i+1}/{args.repeat} ---")
            t1 = time.time()
            res = sweep(base, verbose=True)
            print(f"  ({time.time()-t1:.1f}s)")
            results.append(res)
            if res["counts"]["FAILURE"]:
                all_problems.append(
                    f"sweep {i+1}: {res['counts']['FAILURE']} combination(s) failed")

        print("\n--- presets: unchanged, and on the same path as free selection ---")
        preset_problems = check_presets(base, verbose=True)
        all_problems += preset_problems
        for p in preset_problems:
            print(f"  ! {p}")
    finally:
        srv.shutdown()

    r = results[0]
    c = r["counts"]
    ok = not all_problems
    print("\n" + "=" * 72)
    print(f"SWEPT {r['total']} combinations through the real HTTP endpoint")
    print(f"  scored {c['scored']}  |  no-decision {c['no-decision']}  |  "
          f"refused cleanly {c['refused']}  |  failures {c['FAILURE']}")
    print("NO LIVE IMD CALL: prior built from cached data (asserted in build_case)")
    print("GATE:", "PASS -- every reachable combination is scored or cleanly refused"
          if ok else f"FAIL -- {len(all_problems)} problem(s)")
    for p in all_problems:
        print(f"  ! {p}")
    print("=" * 72)

    with open(ARTIFACT, "w", encoding="utf-8") as f:
        f.write("PER-FARMER PROFILE SCREEN -- full combination sweep (D-28)\n")
        f.write("case: 2018-07-15 (shared prior); driven over real HTTP, ephemeral port\n\n")
        f.write(f"combinations swept        : {r['total']}\n")
        f.write(f"  scored (SOW/WAIT)       : {c['scored']}"
                f"   [sow {r['recommendations']['sow']} / wait {r['recommendations']['wait']}]\n")
        f.write(f"  no-decision (sown)      : {c['no-decision']}\n")
        f.write(f"  refused (clean 400)     : {c['refused']}\n")
        f.write(f"  failures                : {c['FAILURE']}\n\n")
        f.write("presets A/B/C/D: rehearsed recommendations held, and each matches\n")
        f.write("its free-form equivalent payload exactly (one decision path).\n\n")
        f.write(f"result: {'PASS' if ok else 'FAIL'}\n")
        for p in all_problems:
            f.write(f"  ! {p}\n")
    print(f"\nwrote {ARTIFACT}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

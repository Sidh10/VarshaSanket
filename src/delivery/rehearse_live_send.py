"""Rehearsal script -- sends ONE REAL WhatsApp message. Run once before presenting.

    python -m src.delivery.rehearse_live_send --confirm-live-send

WHAT MAKES THIS DIFFERENT FROM run_demo.py
-----------------------------------------
`src/demo/run_demo.py` is offline and idempotent -- it is safe in the regression
suite. THIS script is not: every successful run delivers a real message to the
demo phone via the Twilio WhatsApp Sandbox. It therefore:

  * refuses to run without the explicit `--confirm-live-send` flag,
  * is named `rehearse_*` (not `run_*` / `test_*`) so no test collector picks
    it up,
  * is imported by nothing.

WHEN TO RUN IT
--------------
A few MINUTES before presenting, not seconds. If the check fails because the
24-hour WhatsApp session window has closed (D-21), the fix is to send the
sandbox join phrase from the demo phone and wait for it to register -- you need
slack for that, not a countdown.

WHY THE REAL ADVISORY, NOT A "test" STRING
-----------------------------------------
It sends the actual 2018-07-15 soybean advisory -- the real Phase 4b output.
That is the only way to confirm it renders correctly on a physical phone: line
breaks, the 1000+ character length, no broken formatting. The browser demo
cannot check that.

ENVIRONMENT (all four required)
-------------------------------
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM     the sandbox number, e.g. "whatsapp:+14155238886"
    VARSHASANKET_DEMO_TO     the demo phone in E.164, e.g. "+9198XXXXXXXX"
"""

from __future__ import annotations

import argparse
import os
import sys

_REQUIRED_ENV = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_FROM",
    "VARSHASANKET_DEMO_TO",
)

_BANNER = """\
================================================================================
 REHEARSAL LIVE SEND -- this delivers a REAL WhatsApp message to the demo phone.
 Not for the regression suite. Run it once, a few minutes before presenting.
 Re-run: `python -m src.delivery.rehearse_live_send --confirm-live-send`
================================================================================"""


def _build_real_advisory():
    """The actual 2018-07-15 soybean advisory -- real Phase 4b output."""
    from src.delivery.advisory import render
    from src.demo.case import build_case

    case = build_case()
    result = case.decide_at(case.l_reseed_default)  # canonical theta=1.5 case
    return render(result, case.prior, "en"), result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="rehearse_live_send",
        description="Send the real 2018-07-15 advisory to the demo phone (one real message).",
    )
    ap.add_argument(
        "--confirm-live-send",
        action="store_true",
        help="required -- affirms you intend to send a real WhatsApp message now",
    )
    args = ap.parse_args(argv)

    print(_BANNER)

    if not args.confirm_live_send:
        print(
            "\nREFUSING TO RUN: this sends a real message. Re-invoke with\n"
            "  python -m src.delivery.rehearse_live_send --confirm-live-send\n"
        )
        return 2

    # 1. environment -- name the specific missing variable(s)
    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        print("\nMISSING ENVIRONMENT VARIABLE(S):")
        for v in missing:
            print(f"  - {v}")
        print(
            "\nSet all four, then re-run. TWILIO_WHATSAPP_FROM is the sandbox "
            "number (whatsapp:+1...); VARSHASANKET_DEMO_TO is the demo phone "
            "(+9198...).\n"
        )
        return 1

    to = os.environ["VARSHASANKET_DEMO_TO"].strip()
    frm = os.environ["TWILIO_WHATSAPP_FROM"].strip()
    print(f"\nAll four env vars set.  from={frm}  to={to}")

    # 2. build + show the real advisory before sending
    advisory, result = _build_real_advisory()
    print("\n--- message that will be sent (real Phase 4b output) ---")
    print(advisory.text)
    print("--- end ---")
    print(
        f"language={advisory.language} (verified={advisory.verified_language})  "
        f"chars={advisory.char_count}  lines={advisory.text.count(chr(10)) + 1}  "
        f"recommendation={result.recommendation.upper()}  "
        f"evidence_lines={len(advisory.evidence_lines)}  "
        f"ICAR_disclosure={advisory.disclosure_shown}"
    )
    if advisory.char_count > 1600:
        print(
            f"\nWARNING: {advisory.char_count} chars exceeds WhatsApp's 1600-char "
            f"single-message limit; it will be split. Shorten before the demo."
        )

    # 3. send for real
    from src.delivery.whatsapp import WhatsAppSender

    print("\nsending ...")
    res = WhatsAppSender(dry_run=False).send(to, advisory, recipient_in_session=True)

    # 4. check the STATUS field, not just exception-or-not
    if res.accepted_for_delivery:
        print(
            f"\nOK -- Twilio accepted the message.\n"
            f"  SID    : {res.sid}\n"
            f"  status : {res.status}\n"
            f"\ndelivered -- check the demo phone now. Confirm the text renders "
            f"cleanly: line breaks intact, full length received, no cut-off.\n"
        )
        return 0

    # 5. session-window failure -> the specific fix, in plain language
    if res.session_window_closed:
        join_hint = frm.replace("whatsapp:", "")
        print(
            "\nFAILED -- the WhatsApp session window is closed (or the demo phone "
            "never opted in).\n"
            "\nFIX (do this now, then re-run this script):\n"
            f"  1. On the demo phone, open WhatsApp and message {join_hint}\n"
            f"     with your sandbox join phrase -- it looks like  join two-words\n"
            f"     (find the exact phrase in Twilio Console -> Messaging -> Try it\n"
            f"     out -> WhatsApp sandbox).\n"
            "  2. Wait for the 'connected to sandbox' reply.\n"
            "  3. Re-run:  python -m src.delivery.rehearse_live_send --confirm-live-send\n"
            f"\n(raw: {res.status})\n"
        )
        return 1

    # 6. any other failure -> Twilio's actual message, not a generalization
    print(
        "\nFAILED -- send did not succeed.\n"
        f"  Twilio said: {res.status}\n"
        f"  SID        : {res.sid or '(none)'}\n"
        f"  error_code : {res.error_code if res.error_code is not None else '(none)'}\n"
        "\nThis is Twilio's verbatim response. Do not proceed to the demo until "
        "it sends.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Twilio WhatsApp Sandbox delivery.

WHY THE SANDBOX
---------------
RESEARCH.md (verified): "Twilio WhatsApp Sandbox is free, requires no business
verification." A recipient opts in once by sending a join code to the Twilio
sandbox number; after that the sandbox can message them. That is enough for a
demo and needs no Meta business review.

THE 24-HOUR SESSION WINDOW -- an explicit precondition, not a silent assumption
-----------------------------------------------------------------------------
WhatsApp only allows free-form outbound messages within 24 hours of the
recipient's last inbound message. Outside that window you need an approved Meta
message template. This module does NOT track inbound messages or session state
-- for the demo that state is externally true (the farmer joins / messages the
sandbox, matching D-21 path (a)), and for production the real path is an
approved template (D-21 path (b), out of scope).

Rather than assume the window is open, `send()` takes `recipient_in_session`.
The caller must affirm that the recipient has messaged within the last 24 hours
(or just joined the sandbox). Default False -> dry run with a clear reason, the
same shape as `allow_unverified_language`. If a live send still lands outside
the window, Twilio's out-of-session error is surfaced verbatim in the result.

WHAT THIS MODULE DOES AND DOES NOT DO
------------------------------------
  * DOES: format an `Advisory` into a WhatsApp message and, when real
    credentials are present AND `dry_run=False` is explicitly passed, send it
    via Twilio's REST API.
  * DOES NOT: ship credentials, send anything by default, or fetch any data.
    `dry_run=True` is the default and `send()` refuses to go live without both
    an explicit `dry_run=False` and all three credentials in the environment.

Credentials come from the environment only:
    TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN
    TWILIO_WHATSAPP_FROM   e.g. "whatsapp:+14155238886"  (the sandbox number)

DEFAULT SEND LANGUAGE
--------------------
`en` -- the only rendering treated as verified (advisory.VERIFIED_LANGUAGES).
Sending an unverified `hi` message requires passing it explicitly; `send()`
warns loudly when asked to.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.delivery.advisory import VERIFIED_LANGUAGES, Advisory

_ENV = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM")

# Twilio error codes for a message sent outside the 24-hour session window /
# to a recipient who never opted in. Surfaced verbatim if a live send hits them.
_OUT_OF_SESSION_CODES = {63015, 63016, 63018, 63024, 21610}

SANDBOX_JOIN_HELP = (
    "Twilio WhatsApp Sandbox setup:\n"
    "  1. Twilio Console -> Messaging -> Try it out -> Send a WhatsApp message.\n"
    "  2. From the recipient's phone, WhatsApp the sandbox number the join code\n"
    "     shown there (e.g. 'join <two-words>').  <-- this is the opt-in.\n"
    "  3. Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM in\n"
    "     the environment. No business verification required.\n"
    "  4. Outbound free-form messages work for 24h after the farmer's last\n"
    "     inbound message. Past that: an approved Meta template (production).\n"
)


@dataclass(frozen=True)
class SendResult:
    dry_run: bool
    to: str
    from_: str | None
    language: str
    verified_language: bool
    body: str
    sid: str | None
    status: str

    def describe(self) -> str:
        head = "DRY RUN (not sent)" if self.dry_run else f"SENT sid={self.sid} status={self.status}"
        return (
            f"[WhatsApp] {head}\n"
            f"  to={self.to}  from={self.from_ or '(unset)'}  "
            f"lang={self.language} ({'verified' if self.verified_language else 'UNVERIFIED'})\n"
            f"--- body ---\n{self.body}\n--- end ---"
        )


def _credentials() -> dict[str, str] | None:
    vals = {k: os.environ.get(k) for k in _ENV}
    return vals if all(vals.values()) else None


class WhatsAppSender:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def send(
        self,
        to: str,
        advisory: Advisory,
        recipient_in_session: bool = False,
        allow_unverified_language: bool = False,
    ) -> SendResult:
        """Send one advisory. `to` is a bare phone number in E.164, e.g. +9198...

        Refuses to go live unless ALL of:
          * `self.dry_run is False`
          * all three TWILIO_* env vars are set
          * `recipient_in_session=True` -- the caller affirms the farmer messaged
            the number within the last 24h (or just joined the sandbox). This is
            the opt-in / session-window precondition; it is not tracked here.
          * the language is verified, or `allow_unverified_language=True`

        Any unmet precondition returns a dry-run `SendResult` naming it, rather
        than raising -- except a bad language, which raises (a farmer must never
        get unreviewed text). If a live send still lands outside the window,
        Twilio's error is surfaced in `status`.
        """
        if not advisory.verified_language and not allow_unverified_language:
            raise ValueError(
                f"advisory language {advisory.language!r} is not in "
                f"{VERIFIED_LANGUAGES} and has not been reviewed. Refusing to "
                f"send. Pass allow_unverified_language=True only for internal "
                f"testing, never a real farmer."
            )

        creds = _credentials()
        to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"

        blockers = []
        if self.dry_run:
            blockers.append("dry_run=True")
        if creds is None:
            blockers.append("no credentials in env")
        if not recipient_in_session:
            blockers.append(
                "recipient_in_session=False (no confirmed opt-in / 24h window)"
            )
        if blockers:
            return SendResult(
                dry_run=True,
                to=to_wa,
                from_=creds["TWILIO_WHATSAPP_FROM"] if creds else None,
                language=advisory.language,
                verified_language=advisory.verified_language,
                body=advisory.text,
                sid=None,
                status="not sent (" + "; ".join(blockers) + ")",
            )

        from twilio.rest import Client  # imported only on a real send
        from twilio.base.exceptions import TwilioRestException

        client = Client(creds["TWILIO_ACCOUNT_SID"], creds["TWILIO_AUTH_TOKEN"])
        try:
            msg = client.messages.create(
                from_=creds["TWILIO_WHATSAPP_FROM"], to=to_wa, body=advisory.text
            )
        except TwilioRestException as e:
            hint = (
                "  -- recipient is outside the 24h session window or never "
                "opted in; needs an inbound message or an approved template"
                if e.code in _OUT_OF_SESSION_CODES
                else ""
            )
            return SendResult(
                dry_run=False,
                to=to_wa,
                from_=creds["TWILIO_WHATSAPP_FROM"],
                language=advisory.language,
                verified_language=advisory.verified_language,
                body=advisory.text,
                sid=None,
                status=f"send failed (Twilio {e.code}: {e.msg}){hint}",
            )
        return SendResult(
            dry_run=False,
            to=to_wa,
            from_=creds["TWILIO_WHATSAPP_FROM"],
            language=advisory.language,
            verified_language=advisory.verified_language,
            body=advisory.text,
            sid=msg.sid,
            status=msg.status,
        )

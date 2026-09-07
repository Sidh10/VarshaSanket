"""Twilio WhatsApp Sandbox delivery.

WHY THE SANDBOX
---------------
RESEARCH.md (verified): "Twilio WhatsApp Sandbox is free, requires no business
verification." A recipient opts in once by sending a join code to the Twilio
sandbox number; after that the sandbox can message them. That is enough for a
demo and needs no Meta business review.

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
SANDBOX_JOIN_HELP = (
    "Twilio WhatsApp Sandbox setup:\n"
    "  1. Twilio Console -> Messaging -> Try it out -> Send a WhatsApp message.\n"
    "  2. From the recipient's phone, WhatsApp the sandbox number the join code\n"
    "     shown there (e.g. 'join <two-words>').\n"
    "  3. Set TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM in\n"
    "     the environment. No business verification required.\n"
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

    def send(self, to: str, advisory: Advisory, allow_unverified_language: bool = False) -> SendResult:
        """Send one advisory. `to` is a bare phone number in E.164, e.g. +9198...

        Refuses to go live unless `self.dry_run is False` AND all three env vars
        are set. Refuses an unverified-language message unless
        `allow_unverified_language=True` is passed on purpose.
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

        if self.dry_run or creds is None:
            reason = "dry_run=True" if self.dry_run else "no credentials in env"
            return SendResult(
                dry_run=True,
                to=to_wa,
                from_=creds["TWILIO_WHATSAPP_FROM"] if creds else None,
                language=advisory.language,
                verified_language=advisory.verified_language,
                body=advisory.text,
                sid=None,
                status=f"not sent ({reason})",
            )

        from twilio.rest import Client  # imported only on a real send

        client = Client(creds["TWILIO_ACCOUNT_SID"], creds["TWILIO_AUTH_TOKEN"])
        msg = client.messages.create(
            from_=creds["TWILIO_WHATSAPP_FROM"],
            to=to_wa,
            body=advisory.text,
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

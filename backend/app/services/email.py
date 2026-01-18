from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import settings


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: Optional[str] = None
    from_email: Optional[str] = None


class EmailService:
    """
    Provider-agnostic email sender.

    Development default: stub mode (prints to logs).
    Swap later with SMTP/SendGrid/SES/Mailgun/etc.
    """

    async def send(self, msg: EmailMessage) -> None:
        mode = getattr(settings, "EMAIL_MODE", "stub").strip().lower()
        if mode == "stub":
            self._stub_send(msg)
            return

        # Future: implement provider routing here
        # raise NotImplementedError(f"EMAIL_MODE '{mode}' not implemented yet.")
        self._stub_send(msg)

    def _stub_send(self, msg: EmailMessage) -> None:
        from_email = msg.from_email or getattr(settings, "EMAIL_FROM", "no-reply@postika.co.ke")
        print("=== EMAIL STUB ===")
        print(f"To: {msg.to}")
        print(f"From: {from_email}")
        print(f"Subject: {msg.subject}")
        if msg.text:
            print("--- TEXT ---")
            print(msg.text)
        print("--- HTML ---")
        print(msg.html)
        print("=== END EMAIL STUB ===")


email_service = EmailService()

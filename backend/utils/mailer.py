import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Sequence, Optional

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", os.getenv("MAIL_SENDER", "no-reply@ticklegram.com"))
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TickleGram")


def _format_sender(custom_sender: Optional[str]) -> Optional[str]:
    if custom_sender:
        return custom_sender
    if not SMTP_FROM_EMAIL:
        return None
    return formataddr((SMTP_FROM_NAME, SMTP_FROM_EMAIL))


def _is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM_EMAIL)


def send_email(
    subject: str,
    body_text: str,
    to_addresses: Sequence[str],
    body_html: Optional[str] = None,
    sender: Optional[str] = None,
) -> bool:
    """
    Send an email via the configured SMTP relay.

    Returns True when the message is handed to the SMTP server, False otherwise.
    """
    recipients = [addr for addr in to_addresses if addr]
    if not recipients:
        return False

    if not _is_configured():
        logger.info(
            "SMTP mailer not configured; skipping email. Subject=%s Recipients=%s",
            subject,
            recipients,
        )
        return False

    from_header = _format_sender(sender)
    if not from_header:
        logger.warning("Missing SMTP_FROM_EMAIL; cannot send password reset email.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = ", ".join(recipients)
    message.set_content(body_text or "", subtype="plain", charset="utf-8")

    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASS or "")
            smtp.send_message(message)
        return True
    except Exception as exc:  # pragma: no cover - log SMTP failures
        logger.error("SMTP send_email failed: %s", exc)
        return False

"""Provider-neutral delivery adapters for AUTH-001 transactional email."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from threading import Lock

from config import AppSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuthEmail:
    purpose: str
    recipient: str
    subject: str
    text: str
    action_url: str


class AuthEmailSender:
    """Small delivery contract independent of SMTP/provider details."""

    backend_name = "unknown"
    available = False

    def send(self, message: AuthEmail) -> bool:
        raise NotImplementedError


class DisabledAuthEmailSender(AuthEmailSender):
    backend_name = "disabled"
    available = False

    def send(self, message: AuthEmail) -> bool:
        logger.warning(
            "Auth email delivery skipped",
            extra={
                "event": "auth_email_delivery_skipped",
                "purpose": message.purpose,
                "delivery_backend": self.backend_name,
            },
        )
        return False


class MemoryAuthEmailSender(AuthEmailSender):
    """Deterministic no-network test backend. Never selected in production."""

    backend_name = "memory"
    available = True

    def __init__(self) -> None:
        self._messages: list[AuthEmail] = []
        self._lock = Lock()

    def send(self, message: AuthEmail) -> bool:
        with self._lock:
            self._messages.append(message)
        return True

    def latest(self, purpose: str | None = None) -> AuthEmail | None:
        with self._lock:
            for message in reversed(self._messages):
                if purpose is None or message.purpose == purpose:
                    return message
        return None

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()


class SMTPAuthEmailSender(AuthEmailSender):
    backend_name = "smtp"
    available = True

    def __init__(self, settings: AppSettings) -> None:
        self.host = settings.auth_smtp_host or ""
        self.port = settings.auth_smtp_port
        self.username = settings.auth_smtp_username
        self.password = settings.auth_smtp_password
        self.use_tls = settings.auth_smtp_use_tls
        self.timeout = settings.auth_smtp_timeout_seconds
        self.from_email = settings.auth_email_from or ""
        self.from_name = settings.auth_email_from_name

    def send(self, message: AuthEmail) -> bool:
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = formataddr((self.from_name, self.from_email))
        email["To"] = message.recipient
        email.set_content(message.text)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as client:
                client.ehlo()
                if self.use_tls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if self.username:
                    client.login(self.username, self.password or "")
                client.send_message(email)
        except (OSError, smtplib.SMTPException) as exc:
            # Deliberately omit exception text/traceback: SMTP responses may
            # include account identifiers. The error type is enough for the
            # public-safe operational signal.
            logger.warning(
                "Auth email delivery failed",
                extra={
                    "event": "auth_email_delivery_failed",
                    "purpose": message.purpose,
                    "delivery_backend": self.backend_name,
                    "error_type": type(exc).__name__,
                },
            )
            return False
        logger.info(
            "Auth email delivered",
            extra={
                "event": "auth_email_delivered",
                "purpose": message.purpose,
                "delivery_backend": self.backend_name,
            },
        )
        return True


def build_auth_email_sender(settings: AppSettings) -> AuthEmailSender:
    if settings.auth_email_backend == "memory":
        return MemoryAuthEmailSender()
    if settings.auth_email_backend == "smtp":
        return SMTPAuthEmailSender(settings)
    return DisabledAuthEmailSender()

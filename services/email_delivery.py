"""Provider-neutral delivery adapters for AUTH-001 transactional email."""

from __future__ import annotations

import base64
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from threading import Lock

import requests

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
        self.use_ssl = settings.auth_smtp_use_ssl
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
            tls_context = ssl.create_default_context()
            if self.use_ssl:
                smtp_client = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout,
                    context=tls_context,
                )
            else:
                smtp_client = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

            with smtp_client as client:
                client.ehlo()
                if self.use_tls:
                    client.starttls(context=tls_context)
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


class GmailApiAuthEmailSender(AuthEmailSender):
    """HTTPS Gmail API delivery for staging environments where SMTP egress is unavailable."""

    backend_name = "gmail_api"
    available = True
    token_url = "https://oauth2.googleapis.com/token"
    send_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    def __init__(self, settings: AppSettings) -> None:
        self.client_id = settings.auth_gmail_client_id or ""
        self.client_secret = settings.auth_gmail_client_secret or ""
        self.refresh_token = settings.auth_gmail_refresh_token or ""
        self.timeout = settings.auth_gmail_timeout_seconds
        self.from_email = settings.auth_email_from or ""
        self.from_name = settings.auth_email_from_name

    def _access_token(self) -> str:
        response = requests.post(
            self.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("Gmail OAuth token response is missing access_token")
        return access_token.strip()

    def _log_failure(self, message: AuthEmail, exc: Exception, *, stage: str) -> None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        # Deliberately omit exception text/response body. OAuth errors may
        # contain account/provider details and tokens must never reach logs.
        logger.warning(
            "Auth email delivery failed",
            extra={
                "event": "auth_email_delivery_failed",
                "purpose": message.purpose,
                "delivery_backend": self.backend_name,
                "delivery_stage": stage,
                "provider_status_code": status_code,
                "error_type": type(exc).__name__,
            },
        )

    def send(self, message: AuthEmail) -> bool:
        email = EmailMessage()
        email["Subject"] = message.subject
        email["From"] = formataddr((self.from_name, self.from_email))
        email["To"] = message.recipient
        email.set_content(message.text)
        raw_message = base64.urlsafe_b64encode(email.as_bytes()).decode("ascii")

        try:
            access_token = self._access_token()
        except (OSError, requests.RequestException, TypeError, ValueError) as exc:
            self._log_failure(message, exc, stage="token_refresh")
            return False

        try:
            response = requests.post(
                self.send_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw_message},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except (OSError, requests.RequestException, TypeError, ValueError) as exc:
            self._log_failure(message, exc, stage="message_send")
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
    if settings.auth_email_backend == "gmail_api":
        return GmailApiAuthEmailSender(settings)
    return DisabledAuthEmailSender()

from __future__ import annotations

import base64
from email import message_from_bytes
from types import SimpleNamespace

import requests

from services.email_delivery import (
    AuthEmail,
    GmailApiAuthEmailSender,
    SMTPAuthEmailSender,
    build_auth_email_sender,
)


def _settings(*, use_tls: bool, use_ssl: bool, backend: str = "smtp"):
    return SimpleNamespace(
        auth_email_backend=backend,
        auth_smtp_host="smtp.example.test",
        auth_smtp_port=465 if use_ssl else 587,
        auth_smtp_username="accounts@example.test",
        auth_smtp_password="app-password",
        auth_smtp_use_tls=use_tls,
        auth_smtp_use_ssl=use_ssl,
        auth_smtp_timeout_seconds=8.0,
        auth_gmail_client_id="client-id.apps.googleusercontent.com",
        auth_gmail_client_secret="client-secret",
        auth_gmail_refresh_token="refresh-token",
        auth_gmail_timeout_seconds=8.0,
        auth_email_from="accounts@example.test",
        auth_email_from_name="AI Career Agent",
    )


def _message():
    return AuthEmail(
        purpose="email_verification",
        recipient="user@example.test",
        subject="Verify",
        text="Verification body",
        action_url="https://example.test/auth/verify?token=redacted",
    )


class _FakeSMTP:
    def __init__(self, calls, *args, **kwargs):
        self.calls = calls
        self.calls.append(("connect", args, kwargs))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.calls.append(("close",))

    def ehlo(self):
        self.calls.append(("ehlo",))

    def starttls(self, *, context):
        self.calls.append(("starttls", bool(context)))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, email):
        self.calls.append(("send_message", email["From"], email["To"]))


class _FakeResponse:
    def __init__(self, *, payload=None, error: Exception | None = None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


def test_smtp_sender_uses_starttls_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "services.email_delivery.smtplib.SMTP",
        lambda *args, **kwargs: _FakeSMTP(calls, *args, **kwargs),
    )
    monkeypatch.setattr(
        "services.email_delivery.smtplib.SMTP_SSL",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("SMTP_SSL must not be used")),
    )

    sender = SMTPAuthEmailSender(_settings(use_tls=True, use_ssl=False))
    assert sender.send(_message()) is True

    assert calls[0][0] == "connect"
    assert calls[0][1][:2] == ("smtp.example.test", 587)
    assert [call[0] for call in calls].count("starttls") == 1
    assert any(call[0] == "login" for call in calls)
    assert any(call[0] == "send_message" for call in calls)


def test_smtp_sender_uses_implicit_ssl_without_starttls(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "services.email_delivery.smtplib.SMTP_SSL",
        lambda *args, **kwargs: _FakeSMTP(calls, *args, **kwargs),
    )
    monkeypatch.setattr(
        "services.email_delivery.smtplib.SMTP",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("plain SMTP must not be used")),
    )

    sender = SMTPAuthEmailSender(_settings(use_tls=False, use_ssl=True))
    assert sender.send(_message()) is True

    assert calls[0][0] == "connect"
    assert calls[0][1][:2] == ("smtp.example.test", 465)
    assert "context" in calls[0][2]
    assert not any(call[0] == "starttls" for call in calls)
    assert any(call[0] == "login" for call in calls)
    assert any(call[0] == "send_message" for call in calls)


def test_gmail_api_sender_refreshes_token_and_sends_rfc2822_message(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if url == GmailApiAuthEmailSender.token_url:
            return _FakeResponse(payload={"access_token": "access-token", "expires_in": 3600})
        if url == GmailApiAuthEmailSender.send_url:
            return _FakeResponse(payload={"id": "gmail-message-id"})
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("services.email_delivery.requests.post", fake_post)
    sender = GmailApiAuthEmailSender(
        _settings(use_tls=False, use_ssl=False, backend="gmail_api")
    )

    assert sender.send(_message()) is True
    assert len(calls) == 2

    token_url, token_kwargs = calls[0]
    assert token_url == GmailApiAuthEmailSender.token_url
    assert token_kwargs["data"] == {
        "client_id": "client-id.apps.googleusercontent.com",
        "client_secret": "client-secret",
        "refresh_token": "refresh-token",
        "grant_type": "refresh_token",
    }
    assert token_kwargs["timeout"] == 8.0

    send_url, send_kwargs = calls[1]
    assert send_url == GmailApiAuthEmailSender.send_url
    assert send_kwargs["headers"]["Authorization"] == "Bearer access-token"
    raw = send_kwargs["json"]["raw"]
    parsed = message_from_bytes(base64.urlsafe_b64decode(raw.encode("ascii")))
    assert parsed["From"] == "AI Career Agent <accounts@example.test>"
    assert parsed["To"] == "user@example.test"
    assert parsed["Subject"] == "Verify"
    assert "Verification body" in parsed.get_payload()


def test_gmail_api_sender_fails_closed_when_token_refresh_is_rejected(monkeypatch):
    warning_calls = []

    def fake_post(url, **kwargs):
        assert url == GmailApiAuthEmailSender.token_url
        response = requests.Response()
        response.status_code = 400
        raise requests.HTTPError("provider response must not be logged", response=response)

    def fake_warning(message, *, extra):
        warning_calls.append((message, extra))

    monkeypatch.setattr("services.email_delivery.requests.post", fake_post)
    monkeypatch.setattr("services.email_delivery.logger.warning", fake_warning)
    sender = GmailApiAuthEmailSender(
        _settings(use_tls=False, use_ssl=False, backend="gmail_api")
    )

    assert sender.send(_message()) is False
    assert len(warning_calls) == 1
    log_message, extra = warning_calls[0]
    assert log_message == "Auth email delivery failed"
    assert extra["event"] == "auth_email_delivery_failed"
    assert extra["delivery_stage"] == "token_refresh"
    assert extra["provider_status_code"] == 400
    serialized = repr(warning_calls)
    assert "provider response must not be logged" not in serialized
    assert "refresh-token" not in serialized


def test_gmail_api_sender_fails_closed_when_send_request_is_rejected(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if url == GmailApiAuthEmailSender.token_url:
            return _FakeResponse(payload={"access_token": "access-token"})
        response = requests.Response()
        response.status_code = 403
        return _FakeResponse(error=requests.HTTPError("send rejected", response=response))

    monkeypatch.setattr("services.email_delivery.requests.post", fake_post)
    sender = GmailApiAuthEmailSender(
        _settings(use_tls=False, use_ssl=False, backend="gmail_api")
    )

    assert sender.send(_message()) is False
    assert calls == [GmailApiAuthEmailSender.token_url, GmailApiAuthEmailSender.send_url]


def test_gmail_api_sender_rejects_token_response_without_access_token(monkeypatch):
    monkeypatch.setattr(
        "services.email_delivery.requests.post",
        lambda *args, **kwargs: _FakeResponse(payload={"token_type": "Bearer"}),
    )
    sender = GmailApiAuthEmailSender(
        _settings(use_tls=False, use_ssl=False, backend="gmail_api")
    )

    assert sender.send(_message()) is False


def test_sender_factory_selects_gmail_api_backend():
    sender = build_auth_email_sender(
        _settings(use_tls=False, use_ssl=False, backend="gmail_api")
    )

    assert isinstance(sender, GmailApiAuthEmailSender)
    assert sender.backend_name == "gmail_api"
    assert sender.available is True

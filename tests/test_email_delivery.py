from __future__ import annotations

from types import SimpleNamespace

from services.email_delivery import AuthEmail, SMTPAuthEmailSender


def _settings(*, use_tls: bool, use_ssl: bool):
    return SimpleNamespace(
        auth_smtp_host="smtp.example.test",
        auth_smtp_port=465 if use_ssl else 587,
        auth_smtp_username="accounts@example.test",
        auth_smtp_password="app-password",
        auth_smtp_use_tls=use_tls,
        auth_smtp_use_ssl=use_ssl,
        auth_smtp_timeout_seconds=8.0,
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

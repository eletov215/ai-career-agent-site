from __future__ import annotations

import html
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("flask")

from services.email_delivery import MemoryAuthEmailSender


def _csrf(response) -> str:
    body = response.get_data(as_text=True)
    match = re.search(r'name="csrf-token" content="([^"]+)"', body)
    assert match
    return html.unescape(match.group(1))


def _token_from_sender(sender: MemoryAuthEmailSender, purpose: str) -> str:
    message = sender.latest(purpose)
    assert message is not None
    return parse_qs(urlparse(message.action_url).query)["token"][0]


def _register_and_verify(app_module, client, *, email: str, password: str) -> None:
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    token = _csrf(client.get("/auth/register"))
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": token,
            "display_name": "Route Test",
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )
    assert response.status_code == 200
    raw = _token_from_sender(sender, "verify_email")
    verify_page = client.get(f"/auth/verify?token={raw}")
    verified = client.post(
        "/auth/verify",
        data={"csrf_token": _csrf(verify_page), "token": raw},
    )
    assert verified.status_code == 200
    assert "Email подтверждён" in verified.get_data(as_text=True)


def test_auth_pages_are_public_and_render_without_provider_login(client):
    for path in (
        "/auth/register",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/resend-verification",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert "AI Career Agent" in response.get_data(as_text=True)


def test_registration_verification_login_dashboard_and_logout(app_module, client):
    email = f"route-{uuid.uuid4().hex}@example.test"
    password = "Route unique password 42!"
    _register_and_verify(app_module, client, email=email, password=password)

    login_page = client.get("/auth/login?next=/dashboard")
    logged_in = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302
    assert logged_in.headers["Location"].endswith("/dashboard")

    dashboard = client.get("/dashboard")
    body = dashboard.get_data(as_text=True)
    assert dashboard.status_code == 200
    assert email in body
    assert "Email подтверждён" in body
    assert "Текущее устройство" in body

    logout = client.post(
        "/auth/logout",
        data={"csrf_token": _csrf(dashboard)},
        follow_redirects=False,
    )
    assert logout.status_code == 302
    assert client.get("/dashboard").status_code == 302
    assert "/auth/login" in client.get("/dashboard").headers["Location"]


def test_login_rejects_external_next_url(app_module, client):
    email = f"next-{uuid.uuid4().hex}@example.test"
    password = "Next unique password 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    page = client.get("/auth/login?next=https://evil.example/")
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(page),
            "email": email,
            "password": password,
            "next": "https://evil.example/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert "evil.example" not in response.headers["Location"]


def test_forgot_password_response_is_enumeration_safe_and_reset_revokes_session(app_module, client):
    email = f"reset-route-{uuid.uuid4().hex}@example.test"
    password = "Reset route password 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    sender = app_module.AUTH_EMAIL_SENDER

    login_page = client.get("/auth/login")
    client.post(
        "/auth/login",
        data={"csrf_token": _csrf(login_page), "email": email, "password": password, "next": "/dashboard"},
    )
    with client.session_transaction() as browser_session:
        old_session_token = browser_session.get("auth_session_token")
    assert old_session_token

    forgot_page = client.get("/auth/forgot-password")
    known = client.post(
        "/auth/forgot-password",
        data={"csrf_token": _csrf(forgot_page), "email": email},
    )
    forgot_page_unknown = client.get("/auth/forgot-password")
    unknown = client.post(
        "/auth/forgot-password",
        data={"csrf_token": _csrf(forgot_page_unknown), "email": f"unknown-{uuid.uuid4().hex}@example.test"},
    )
    expected = "Если аккаунт существует и действие доступно, письмо будет отправлено."
    assert expected in known.get_data(as_text=True)
    assert expected in unknown.get_data(as_text=True)

    raw_reset = _token_from_sender(sender, "password_reset")
    reset_page = client.get(f"/auth/reset-password?token={raw_reset}")
    new_password = "Updated route password 99!"
    reset = client.post(
        "/auth/reset-password",
        data={
            "csrf_token": _csrf(reset_page),
            "token": raw_reset,
            "password": new_password,
            "password_confirm": new_password,
        },
    )
    assert reset.status_code == 200
    assert "Пароль обновлён" in reset.get_data(as_text=True)
    assert app_module.AUTH_SERVICE.load_session(old_session_token) is None

    old_login = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(client.get("/auth/login")),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
    )
    assert "Неверный email, пароль или email ещё не подтверждён" in old_login.get_data(as_text=True)
    new_login = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(client.get("/auth/login")),
            "email": email,
            "password": new_password,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert new_login.status_code == 302


def test_registration_public_response_does_not_disclose_duplicate_email(app_module, client):
    email = f"duplicate-route-{uuid.uuid4().hex}@example.test"
    password = "Duplicate route password 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    page = client.get("/auth/register")
    # Authenticated users are redirected; log out first.
    with client.session_transaction() as browser_session:
        browser_session.clear()
    page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(page),
            "display_name": "Other",
            "email": email.upper(),
            "password": "Another route password 99!",
            "password_confirm": "Another route password 99!",
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "уже зарегистрирован" not in body.casefold()
    assert "Если адрес можно использовать" in body


def test_auth_token_pages_are_no_store_and_origin_only_referrer(client):
    response = client.get("/auth/verify?token=opaque-test-token")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Referrer-Policy"] == "strict-origin"


def test_first_party_requests_discard_legacy_provider_browser_identities(app_module, client):
    email = f"discard-legacy-{uuid.uuid4().hex}@example.test"
    password = "Discard legacy provider ids 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    login_page = client.get("/auth/login")
    client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
    )
    with client.session_transaction() as browser_session:
        browser_session["hh_user_id"] = "legacy-hh"
        browser_session["superjob_user_id"] = 919

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    with client.session_transaction() as browser_session:
        assert browser_session.get("auth_session_token")
        assert "hh_user_id" not in browser_session
        assert "superjob_user_id" not in browser_session

    response = client.post(
        "/auth/logout",
        data={"csrf_token": _csrf(dashboard)},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with client.session_transaction() as browser_session:
        assert "auth_session_token" not in browser_session
        assert "hh_user_id" not in browser_session
        assert "superjob_user_id" not in browser_session

def test_disabled_email_backend_blocks_account_creation_without_writing_user(app_module, client, monkeypatch):
    sender = app_module.AUTH_EMAIL_SENDER
    monkeypatch.setattr(sender, "available", False)
    email = f"disabled-{uuid.uuid4().hex}@example.test"
    page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(page),
            "display_name": "Disabled",
            "email": email,
            "password": "Disabled unique password 42!",
            "password_confirm": "Disabled unique password 42!",
        },
    )
    assert response.status_code == 503
    assert "ещё не настроен" in response.get_data(as_text=True)
    assert app_module.STORAGE.auth.find_user_by_email(email.casefold()) is None


def test_auth_pages_are_no_store_and_do_not_forward_token_paths(client):
    response = client.get("/auth/verify?token=public-test-token")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Referrer-Policy"] == "strict-origin"


def test_production_https_auth_post_accepts_origin_referrer_and_keeps_strict_csrf(
    app_module,
    client,
):
    app_module.app.config["WTF_CSRF_SSL_STRICT"] = True
    try:
        page = client.get("/auth/register", base_url="https://localhost")
        assert page.status_code == 200
        assert page.headers["Referrer-Policy"] == "strict-origin"
        csrf_token = _csrf(page)

        missing_referrer = client.post(
            "/auth/register",
            base_url="https://localhost",
            data={
                "csrf_token": csrf_token,
                "display_name": "Missing referrer",
                "email": f"missing-referrer-{uuid.uuid4().hex}@example.test",
                "password": "Missing referrer password 42!",
                "password_confirm": "Missing referrer password 42!",
            },
        )
        assert missing_referrer.status_code == 400
        assert "Сессия формы устарела" in missing_referrer.get_data(as_text=True)

        fresh_page = client.get("/auth/register", base_url="https://localhost")
        accepted = client.post(
            "/auth/register",
            base_url="https://localhost",
            headers={"Referer": "https://localhost/"},
            data={
                "csrf_token": _csrf(fresh_page),
                "display_name": "Origin referrer",
                "email": f"origin-referrer-{uuid.uuid4().hex}@example.test",
                "password": "Origin referrer password 42!",
                "password_confirm": "Origin referrer password 42!",
            },
        )
        assert accepted.status_code == 200
        assert "Проверьте почту" in accepted.get_data(as_text=True)
    finally:
        app_module.app.config["WTF_CSRF_SSL_STRICT"] = False


def test_registration_is_unavailable_when_transactional_email_is_disabled(
    app_module,
    client,
    monkeypatch,
):
    monkeypatch.setattr(app_module.AUTH_EMAIL_SENDER, "available", False)
    page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(page),
            "display_name": "Unavailable",
            "email": f"disabled-{uuid.uuid4().hex}@example.test",
            "password": "Delivery unavailable password 42!",
            "password_confirm": "Delivery unavailable password 42!",
        },
    )
    assert response.status_code == 503
    body = response.get_data(as_text=True)
    assert "сервис отправки писем" in body


def test_first_party_login_rotation_clears_legacy_provider_ids(app_module, client):
    email = f"provider-clear-{uuid.uuid4().hex}@example.test"
    password = "Provider ids cleared on login 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    with client.session_transaction() as browser_session:
        browser_session["superjob_user_id"] = 123456
        browser_session["hh_user_id"] = "legacy-hh"

    login_page = client.get("/auth/login")
    logged_in = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302
    with client.session_transaction() as browser_session:
        assert browser_session.get("auth_session_token")
        assert "superjob_user_id" not in browser_session
        assert "hh_user_id" not in browser_session

def test_login_rejects_backslash_based_external_next_url(app_module, client):
    email = f"next-backslash-{uuid.uuid4().hex}@example.test"
    password = "Backslash safe redirect password 42!"
    _register_and_verify(app_module, client, email=email, password=password)
    page = client.get(r"/auth/login?next=/\\evil.example/")
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(page),
            "email": email,
            "password": password,
            "next": r"/\\evil.example/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

from __future__ import annotations

import html
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

pytest.importorskip("flask")

from models import HeadHunterAccount, OAuthConnection, SuperJobAccount
from services.email_delivery import MemoryAuthEmailSender
from tests.fakes import FakeResponse


def _csrf(response) -> str:
    match = re.search(
        r'name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return html.unescape(match.group(1))


def _verification_token(sender: MemoryAuthEmailSender) -> str:
    message = sender.latest("verify_email")
    assert message is not None
    return parse_qs(urlparse(message.action_url).query)["token"][0]


def _register_verify_login(app_module, client, *, prefix: str = "oauth"):
    email = f"{prefix}-{uuid.uuid4().hex}@example.test"
    password = "OAuth binding unique password 42!"
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()

    register = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(register),
            "display_name": "OAuth Route User",
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )
    assert response.status_code == 200
    raw = _verification_token(sender)
    verify = client.get(f"/auth/verify?token={raw}")
    assert client.post(
        "/auth/verify",
        data={"csrf_token": _csrf(verify), "token": raw},
    ).status_code == 200

    login = client.get("/auth/login")
    logged_in = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302
    user = app_module.STORAGE.auth.find_user_by_email(email.casefold())
    assert user is not None
    return user, email, password


def _hh_callback_mocks(
    app_module,
    monkeypatch,
    *,
    external_id: str = "hh-route",
    token: str = "hh-access-new",
):
    def fake_post(url, **kwargs):
        assert url == app_module.HH_TOKEN_URL
        assert kwargs["data"]["code"] == "provider-code"
        return FakeResponse(
            200,
            {
                "access_token": token,
                "refresh_token": "hh-refresh-new",
                "expires_in": 3600,
            },
        )

    def fake_get(url, **kwargs):
        assert url == app_module.HH_ME_URL
        assert kwargs["headers"]["Authorization"] == f"Bearer {token}"
        return FakeResponse(
            200,
            {
                "id": external_id,
                "first_name": "Route",
                "last_name": "HH",
                "email": "route-hh@example.test",
            },
        )

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module.requests, "get", fake_get)


def _superjob_callback_mocks(
    app_module,
    monkeypatch,
    *,
    external_id: int = 505,
    token: str = "sj-access-new",
):
    def fake_post(url, **kwargs):
        assert url == app_module.TOKEN_URL
        assert kwargs["data"]["code"] == "provider-code"
        return FakeResponse(
            200,
            {
                "access_token": token,
                "refresh_token": "sj-refresh-new",
                "expires_in": 3600,
            },
        )

    def fake_get(url, **kwargs):
        assert url == app_module.CURRENT_USER_URL
        assert kwargs["headers"]["Authorization"] == f"Bearer {token}"
        return FakeResponse(
            200,
            {
                "id": external_id,
                "name": "Route SuperJob",
                "email": "route-sj@example.test",
            },
        )

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module.requests, "get", fake_get)


def test_oauth_start_dashboard_and_callbacks_require_first_party_login(client):
    for path in ("/oauth/hh/login", "/oauth/superjob/login", "/dashboard"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    for path in (
        "/oauth/hh/callback?state=secret-state&code=secret-code",
        "/oauth/superjob/callback?state=secret-state&code=secret-code",
    ):
        response = client.get(path, follow_redirects=False)
        body = response.get_data(as_text=True)
        assert response.status_code == 401
        assert "Сессия подключения завершена" in body
        assert "secret-state" not in body
        assert "secret-code" not in body
        assert "next=" not in response.headers.get("Location", "")

    # Legacy provider IDs are neither authentication roots nor persistent state.
    with client.session_transaction() as browser_session:
        browser_session["hh_user_id"] = "legacy-browser-id"
        browser_session["superjob_user_id"] = 123
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as browser_session:
        assert "hh_user_id" not in browser_session
        assert "superjob_user_id" not in browser_session


def test_oauth_state_is_bound_to_first_party_server_session(app_module, client):
    user, email, password = _register_verify_login(app_module, client, prefix="state")
    start = client.get("/oauth/hh/login")
    assert start.status_code == 302
    with client.session_transaction() as browser_session:
        state = browser_session["hh_oauth_state"]
        assert browser_session["hh_oauth_user_id"] == user.id
        original_auth_session_id = browser_session["hh_oauth_auth_session_id"]

    replacement = app_module.AUTH_SERVICE.login(
        email=email,
        password=password,
        user_agent="replacement-session",
    )
    assert replacement.session_token
    replacement_loaded = app_module.AUTH_SERVICE.load_session(replacement.session_token)
    assert replacement_loaded is not None
    assert replacement_loaded.session.id != original_auth_session_id
    with client.session_transaction() as browser_session:
        browser_session["auth_session_token"] = replacement.session_token

    response = client.get(f"/oauth/hh/callback?error=cancelled&state={state}")
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Ошибка безопасности" in body
    with client.session_transaction() as browser_session:
        assert "hh_oauth_state" not in browser_session
        assert browser_session.get("auth_session_token") == replacement.session_token


@pytest.mark.parametrize(
    ("start_path", "callback_path", "state_key", "cancelled_copy"),
    [
        (
            "/oauth/hh/login",
            "/oauth/hh/callback",
            "hh_oauth_state",
            "Подключение HeadHunter было отменено",
        ),
        (
            "/oauth/superjob/login",
            "/oauth/superjob/callback",
            "superjob_oauth_state",
            "Подключение SuperJob было отменено",
        ),
    ],
)
def test_provider_error_requires_valid_owned_state_and_is_not_reflected(
    app_module,
    client,
    start_path,
    callback_path,
    state_key,
    cancelled_copy,
):
    _register_verify_login(app_module, client, prefix="provider-error")
    start = client.get(start_path)
    assert start.status_code == 302
    with client.session_transaction() as browser_session:
        state = browser_session[state_key]

    response = client.get(
        f"{callback_path}?error=secret-provider-detail&state={state}"
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "secret-provider-detail" not in body
    assert cancelled_copy in body
    with client.session_transaction() as browser_session:
        assert state_key not in browser_session


def test_hh_callback_binds_encrypted_identity_to_current_user(
    app_module,
    client,
    monkeypatch,
):
    user, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="hh-success",
    )
    _hh_callback_mocks(app_module, monkeypatch)
    client.get("/oauth/hh/login")
    with client.session_transaction() as browser_session:
        state = browser_session["hh_oauth_state"]

    response = client.get(f"/oauth/hh/callback?code=provider-code&state={state}")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/dashboard")

    connection = app_module.OAUTH_IDENTITIES.get(
        user_id=user.id,
        provider="headhunter",
    )
    assert connection is not None
    assert connection.external_user_id == "hh-route"
    assert connection.access_token != "hh-access-new"
    assert app_module.dec(connection.access_token) == "hh-access-new"
    assert app_module.dec(connection.refresh_token) == "hh-refresh-new"
    with client.session_transaction() as browser_session:
        assert "hh_user_id" not in browser_session
        assert browser_session.get("auth_session_token")

    body = client.get("/dashboard").get_data(as_text=True)
    assert "Route HH" in body
    assert "Подключено к вашему аккаунту" in body
    assert "Отключить" in body


def test_superjob_callback_binds_identity_and_resume_access_is_owner_scoped(
    app_module,
    client,
    monkeypatch,
):
    user, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="sj-success",
    )
    _superjob_callback_mocks(app_module, monkeypatch)
    client.get("/oauth/superjob/login")
    with client.session_transaction() as browser_session:
        state = browser_session["superjob_oauth_state"]

    response = client.get(
        f"/oauth/superjob/callback?code=provider-code&state={state}"
    )
    assert response.status_code == 302
    connection = app_module.OAUTH_IDENTITIES.get(
        user_id=user.id,
        provider="superjob",
    )
    assert connection is not None
    assert connection.external_user_id == "505"
    assert app_module.dec(connection.access_token) == "sj-access-new"
    with client.session_transaction() as browser_session:
        assert "superjob_user_id" not in browser_session
        assert browser_session.get("auth_session_token")

    def resume_get(url, **kwargs):
        assert url == app_module.USER_CVS_URL
        assert kwargs["headers"]["Authorization"] == "Bearer sj-access-new"
        return FakeResponse(200, {"objects": []})

    monkeypatch.setattr(app_module.requests, "get", resume_get)
    body = client.get("/dashboard").get_data(as_text=True)
    assert "Route SuperJob" in body
    assert "Подключено к вашему аккаунту" in body


def test_callback_rejects_identity_owned_by_another_user_without_overwrite(
    app_module,
    client,
    monkeypatch,
):
    owner = app_module.USERS.create(
        email=f"foreign-owner-{uuid.uuid4().hex}@example.test",
        status="active",
    )
    original = app_module.OAUTH_IDENTITIES.connect(
        user_id=owner.id,
        provider="headhunter",
        external_user_id="hh-foreign",
        access_token=app_module.enc("owner-access"),
        refresh_token=app_module.enc("owner-refresh"),
        profile_json="{}",
    ).connection
    current, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="foreign-current",
    )
    assert current.id != owner.id
    _hh_callback_mocks(
        app_module,
        monkeypatch,
        external_id="hh-foreign",
        token="rejected-new-token",
    )
    client.get("/oauth/hh/login")
    with client.session_transaction() as browser_session:
        state = browser_session["hh_oauth_state"]
    response = client.get(f"/oauth/hh/callback?code=provider-code&state={state}")
    body = response.get_data(as_text=True)

    assert response.status_code == 409
    assert "другому аккаунту AI Career Agent" in body
    assert owner.email not in body
    unchanged = app_module.OAUTH_CONNECTIONS.get("headhunter", "hh-foreign")
    assert unchanged is not None
    assert unchanged.id == original.id
    assert unchanged.user_id == owner.id
    assert app_module.dec(unchanged.access_token) == "owner-access"
    assert app_module.OAUTH_IDENTITIES.get(
        user_id=current.id,
        provider="headhunter",
    ) is None


def test_callback_rejects_second_identity_for_same_user_provider(
    app_module,
    client,
    monkeypatch,
):
    user, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="provider-slot",
    )
    existing = app_module.OAUTH_IDENTITIES.connect(
        user_id=user.id,
        provider="headhunter",
        external_user_id="hh-existing",
        access_token=app_module.enc("existing-access"),
        refresh_token=app_module.enc("existing-refresh"),
        profile_json="{}",
    ).connection
    _hh_callback_mocks(
        app_module,
        monkeypatch,
        external_id="hh-different",
        token="different-access",
    )
    client.get("/oauth/hh/login")
    with client.session_transaction() as browser_session:
        state = browser_session["hh_oauth_state"]
    response = client.get(f"/oauth/hh/callback?code=provider-code&state={state}")
    body = response.get_data(as_text=True)

    assert response.status_code == 409
    assert "уже подключён другой аккаунт этой площадки" in body
    unchanged = app_module.OAUTH_IDENTITIES.get(
        user_id=user.id,
        provider="headhunter",
    )
    assert unchanged is not None and unchanged.id == existing.id
    assert app_module.OAUTH_CONNECTIONS.get("headhunter", "hh-different") is None


def test_disconnect_is_post_csrf_owner_scoped_and_clears_legacy_mirror(
    app_module,
    client,
):
    user, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="disconnect",
    )
    connection = app_module.OAUTH_IDENTITIES.connect(
        user_id=user.id,
        provider="superjob",
        external_user_id="707",
        display_name="Disconnect SJ",
        access_token=app_module.enc("disconnect-access"),
        refresh_token=app_module.enc("disconnect-refresh"),
        profile_json="{}",
    ).connection

    assert client.get("/oauth/superjob/disconnect").status_code == 405
    assert client.post("/oauth/superjob/disconnect").status_code == 400
    page = client.get("/")
    response = client.post(
        "/oauth/superjob/disconnect",
        data={"csrf_token": _csrf(page)},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert app_module.OAUTH_IDENTITIES.get(
        user_id=user.id,
        provider="superjob",
    ) is None
    with app_module.DATABASE.session() as session:
        assert session.scalar(
            select(OAuthConnection).where(OAuthConnection.id == connection.id)
        ) is None
        assert session.get(SuperJobAccount, 707) is None


def test_foreign_disconnect_cannot_delete_another_users_connection(
    app_module,
    client,
):
    owner = app_module.USERS.create(
        email=f"disconnect-foreign-{uuid.uuid4().hex}@example.test",
        status="active",
    )
    connection = app_module.OAUTH_IDENTITIES.connect(
        user_id=owner.id,
        provider="headhunter",
        external_user_id="hh-protected",
        access_token=app_module.enc("protected-access"),
        refresh_token=app_module.enc("protected-refresh"),
        profile_json="{}",
    ).connection
    current, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="disconnect-current",
    )
    assert current.id != owner.id

    page = client.get("/")
    response = client.post(
        "/oauth/hh/disconnect",
        data={"csrf_token": _csrf(page)},
        follow_redirects=False,
    )
    assert response.status_code == 302
    unchanged = app_module.OAUTH_CONNECTIONS.get("headhunter", "hh-protected")
    assert unchanged is not None
    assert unchanged.id == connection.id
    assert unchanged.user_id == owner.id
    with app_module.DATABASE.session() as session:
        assert session.get(HeadHunterAccount, "hh-protected") is not None


def test_dashboard_lists_only_current_users_connections(app_module, client):
    current, _email, _password = _register_verify_login(
        app_module,
        client,
        prefix="dashboard-owner",
    )
    other = app_module.USERS.create(
        email=f"dashboard-other-{uuid.uuid4().hex}@example.test",
        status="active",
    )
    app_module.OAUTH_IDENTITIES.connect(
        user_id=current.id,
        provider="headhunter",
        external_user_id=f"hh-current-{uuid.uuid4().hex}",
        display_name="Current HH Identity",
        first_name="Current",
        last_name="HH",
        email="current-hh@example.test",
        access_token=app_module.enc("current-access"),
        refresh_token=app_module.enc("current-refresh"),
        profile_json="{}",
    )
    app_module.OAUTH_IDENTITIES.connect(
        user_id=other.id,
        provider="superjob",
        external_user_id=str(8_000_000 + int(uuid.uuid4().hex[:6], 16)),
        display_name="Foreign SuperJob Identity",
        email="foreign-sj@example.test",
        access_token=app_module.enc("foreign-access"),
        refresh_token=app_module.enc("foreign-refresh"),
        profile_json="{}",
    )

    response = client.get("/dashboard")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Current HH" in body
    assert "current-hh@example.test" in body
    assert "Foreign SuperJob Identity" not in body
    assert "foreign-sj@example.test" not in body

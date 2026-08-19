from __future__ import annotations

import html
import json
import re
import uuid
import zipfile
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

pytest.importorskip("flask")

from models import HeadHunterAccount, OAuthConnection, PrivacyAuditEvent, User
from services.email_delivery import MemoryAuthEmailSender


PASSWORD = "Privacy route password 42!"


def _csrf(response) -> str:
    match = re.search(
        r'<meta name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return html.unescape(match.group(1))


def _register_verify_login(app_module, client, *, email: str) -> str:
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    register_page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(register_page),
            "display_name": "Privacy Route",
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
    )
    assert response.status_code == 200
    message = sender.latest("verify_email")
    assert message is not None
    token = parse_qs(urlparse(message.action_url).query)["token"][0]
    verify_page = client.get(f"/auth/verify?token={token}")
    assert client.post(
        "/auth/verify",
        data={"csrf_token": _csrf(verify_page), "token": token},
    ).status_code == 200
    login_page = client.get("/auth/login")
    logged_in = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": PASSWORD,
            "next": "/privacy-center",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302
    user = app_module.STORAGE.auth.find_user_by_email(email.casefold())
    assert user is not None
    return user.id


def test_privacy_center_requires_login(client):
    assert client.get("/privacy-center", follow_redirects=False).status_code == 302
    assert client.post("/privacy-center/export", follow_redirects=False).status_code in {302, 400}


def test_export_and_confirmed_account_deletion_remove_tokens_and_legacy_mirrors(app_module, client):
    email = f"priv001-{uuid.uuid4().hex}@example.test"
    user_id = _register_verify_login(app_module, client, email=email)

    app_module.STORAGE.oauth_connections.upsert(
        provider="headhunter",
        external_user_id="991177",
        user_id=user_id,
        access_token="DO-NOT-EXPORT-OAUTH-ACCESS",
        refresh_token="DO-NOT-EXPORT-OAUTH-REFRESH",
        profile_json=json.dumps({"city": "Minsk", "note": "owner profile"}),
        display_name="Privacy HH",
        email=email,
    )

    center = client.get("/privacy-center")
    assert center.status_code == 200
    body = center.get_data(as_text=True)
    assert "Скачать мои данные" in body
    assert "Удалить аккаунт" in body

    exported = client.post(
        "/privacy-center/export",
        data={"csrf_token": _csrf(center), "password": PASSWORD},
    )
    assert exported.status_code == 200
    assert exported.mimetype == "application/zip"
    assert "attachment" in exported.headers.get("Content-Disposition", "")
    assert b"DO-NOT-EXPORT-OAUTH-ACCESS" not in exported.data
    assert b"DO-NOT-EXPORT-OAUTH-REFRESH" not in exported.data
    with zipfile.ZipFile(BytesIO(exported.data)) as archive:
        data = json.loads(archive.read("data.json"))
        manifest = json.loads(archive.read("manifest.json"))
    assert data["account"]["email"] == email
    assert data["oauth_connections"][0]["provider"] == "headhunter"
    assert data["oauth_connections"][0]["profile"]["city"] == "Minsk"
    assert manifest["secret_fields_omitted"]

    wrong = client.post(
        "/privacy-center/delete-account",
        data={
            "csrf_token": _csrf(client.get("/privacy-center")),
            "password": PASSWORD,
            "confirmation": "УДАЛИТЬ",
        },
    )
    assert wrong.status_code == 400
    with app_module.DATABASE.session() as db_session:
        assert db_session.get(User, user_id) is not None

    deleted = client.post(
        "/privacy-center/delete-account",
        data={
            "csrf_token": _csrf(client.get("/privacy-center")),
            "password": PASSWORD,
            "confirmation": "УДАЛИТЬ АККАУНТ",
        },
    )
    assert deleted.status_code == 200
    assert "Аккаунт удалён" in deleted.get_data(as_text=True)

    with app_module.DATABASE.session() as db_session:
        assert db_session.get(User, user_id) is None
        assert db_session.scalar(
            select(OAuthConnection).where(OAuthConnection.user_id == user_id)
        ) is None
        assert db_session.get(HeadHunterAccount, "991177") is None
        audit = db_session.scalar(
            select(PrivacyAuditEvent).where(
                PrivacyAuditEvent.event_type == "account_deleted"
            ).order_by(PrivacyAuditEvent.created_at.desc())
        )
        assert audit is not None
        assert user_id not in audit.counts_json
        assert email not in audit.counts_json

    # The deleted account no longer authenticates.
    login_page = client.get("/auth/login")
    relogin = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": PASSWORD,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert relogin.status_code == 401
    assert "Неверный email, пароль или email ещё не подтверждён" in relogin.get_data(as_text=True)

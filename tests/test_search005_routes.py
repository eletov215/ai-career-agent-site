from __future__ import annotations

import html
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("flask")

from services.email_delivery import MemoryAuthEmailSender


def _csrf(response) -> str:
    match = re.search(r'name="csrf-token" content="([^"]+)"', response.get_data(as_text=True))
    assert match
    return html.unescape(match.group(1))


def _register_verify_login(app_module, client, *, email: str, password: str) -> None:
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(page),
            "display_name": "Search Admin Test",
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )
    assert response.status_code == 200
    message = sender.latest("verify_email")
    assert message is not None
    token = parse_qs(urlparse(message.action_url).query)["token"][0]
    verify = client.get(f"/auth/verify?token={token}")
    assert client.post(
        "/auth/verify",
        data={"csrf_token": _csrf(verify), "token": token},
    ).status_code == 200
    login = client.get("/auth/login")
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login),
            "email": email,
            "password": password,
            "next": "/dashboard",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_search005_admin_boundary_and_safe_payload(app_module, client):
    assert client.get("/admin/sources", follow_redirects=False).status_code == 302

    email = f"search-admin-{uuid.uuid4().hex}@example.test"
    password = "Search admin test password 42!"
    _register_verify_login(app_module, client, email=email, password=password)

    old_allowlist = app_module.SETTINGS.search_admin_emails
    try:
        object.__setattr__(app_module.SETTINGS, "search_admin_emails", ())
        assert client.get("/admin/sources").status_code == 404
        assert client.get("/api/admin/sources").status_code == 404

        object.__setattr__(app_module.SETTINGS, "search_admin_emails", (email.casefold(),))
        html_response = client.get("/admin/sources")
        assert html_response.status_code == 200
        assert html_response.headers["Cache-Control"].startswith("no-store")
        assert "ETag" not in html_response.headers
        body = html_response.get_data(as_text=True)
        for title in ("HeadHunter", "SuperJob", "Reed.co.uk", "Работа России"):
            assert title in body

        api = client.get("/api/admin/sources")
        assert api.status_code == 200
        payload = api.get_json()
        assert payload["status"] == "ok"
        assert {item["provider"] for item in payload["sources"]} == {
            "hh", "superjob", "reed", "trudvsem"
        }
        serialized = api.get_data(as_text=True).casefold()
        assert email.casefold() not in serialized
        for forbidden in (
            "access_token",
            "refresh_token",
            "authorization",
            "client_secret",
            "password",
        ):
            assert forbidden not in serialized
    finally:
        object.__setattr__(app_module.SETTINGS, "search_admin_emails", old_allowlist)

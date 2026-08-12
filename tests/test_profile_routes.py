from __future__ import annotations

import html
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("flask")

from services.email_delivery import MemoryAuthEmailSender


def _csrf(response) -> str:
    match = re.search(
        r'<meta name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return html.unescape(match.group(1))


def _register_verify_login(app_module, client, *, email: str) -> None:
    password = "Profile route password 42!"
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    register_page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(register_page),
            "display_name": "Profile Route",
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )
    assert response.status_code == 200
    message = sender.latest("verify_email")
    assert message is not None
    token = parse_qs(urlparse(message.action_url).query)["token"][0]
    verify_page = client.get(f"/auth/verify?token={token}")
    verified = client.post(
        "/auth/verify",
        data={"csrf_token": _csrf(verify_page), "token": token},
    )
    assert verified.status_code == 200
    login_page = client.get("/auth/login")
    logged_in = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": password,
            "next": "/profile",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302


def _profile_payload(csrf_token: str, *, version: int = 0, headline: str = "Backend engineer") -> dict:
    return {
        "csrf_token": csrf_token,
        "expected_version": str(version),
        "headline": headline,
        "summary": "Разрабатываю надёжные web-сервисы.",
        "contact_email": "career-route@example.test",
        "phone": "+7 900 000-00-00",
        "telegram": "@route_profile",
        "portfolio_url": "https://portfolio.example.test",
        "linkedin_url": "",
        "target_roles": "Backend engineer\nTech lead",
        "industries": "SaaS",
        "employment_types": "full",
        "work_formats": "remote",
        "current_location": "Минск",
        "preferred_locations": "Минск\nУдалённо",
        "relocation": "consider",
        "salary_minimum": "300000",
        "salary_maximum": "450000",
        "salary_currency": "RUB",
        "salary_period": "month",
        "salary_tax_mode": "net",
        "skill_name": "Python",
        "skill_level": "advanced",
        "employment_company": "Example",
        "employment_position": "Senior engineer",
        "employment_start": "2022-01",
        "employment_current": "1",
        "employment_end": "",
        "employment_description": "Проектирование и разработка.",
        "achievement_title": "Запуск платформы",
        "achievement_year": "2025",
        "achievement_description": "Запуск без простоя.",
        "education_institution": "БГУ",
        "education_degree": "Бакалавр",
        "education_field": "Информатика",
        "education_start_year": "2014",
        "education_end_year": "2018",
        "education_description": "",
        "language_name": "Английский",
        "language_level": "b2",
    }


def test_profile_routes_require_first_party_session(client):
    for path in ("/profile", "/profile/edit", "/profile/history", "/profile/history/1"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_profile_create_view_history_and_dashboard_summary(app_module, client):
    email = f"profile-route-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)

    empty = client.get("/profile")
    assert empty.status_code == 200
    assert "Профиль ещё не создан" in empty.get_data(as_text=True)
    edit_page = client.get("/profile/edit")
    assert edit_page.status_code == 200
    assert "Неполный профиль допустим" in edit_page.get_data(as_text=True)

    saved = client.post(
        "/profile/edit",
        data=_profile_payload(_csrf(edit_page)),
        follow_redirects=False,
    )
    assert saved.status_code == 302
    assert saved.headers["Location"].endswith("/profile")

    profile = client.get("/profile")
    body = profile.get_data(as_text=True)
    assert profile.status_code == 200
    assert "Backend engineer" in body
    assert "Python" in body
    assert "Версия 1" in body
    assert profile.headers["Cache-Control"] == "no-store, max-age=0"

    history = client.get("/profile/history")
    assert history.status_code == 200
    assert "Версия 1" in history.get_data(as_text=True)
    version = client.get("/profile/history/1")
    assert version.status_code == 200
    assert "Исторический снимок" in version.get_data(as_text=True)
    assert "Backend engineer" in version.get_data(as_text=True)

    dashboard = client.get("/dashboard")
    dashboard_body = dashboard.get_data(as_text=True)
    assert dashboard.status_code == 200
    assert "Карьерный профиль" in dashboard_body
    assert "Версия 1" in dashboard_body


def test_profile_routes_allow_incomplete_profile_and_reject_stale_or_invalid_posts(app_module, client):
    email = f"profile-validation-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)

    page = client.get("/profile/edit")
    created = client.post(
        "/profile/edit",
        data={
            "csrf_token": _csrf(page),
            "expected_version": "0",
            "headline": "",
            "summary": "",
            "relocation": "consider",
            "salary_period": "month",
            "salary_tax_mode": "unspecified",
        },
        follow_redirects=False,
    )
    assert created.status_code == 302

    current = client.get("/profile/edit")
    current_token = _csrf(current)
    updated = client.post(
        "/profile/edit",
        data=_profile_payload(current_token, version=1, headline="Platform engineer"),
        follow_redirects=False,
    )
    assert updated.status_code == 302

    stale_page = client.get("/profile/edit")
    stale = client.post(
        "/profile/edit",
        data=_profile_payload(_csrf(stale_page), version=1, headline="Stale value"),
    )
    assert stale.status_code == 409
    assert "изменён в другой сессии" in stale.get_data(as_text=True)

    invalid_page = client.get("/profile/edit")
    invalid_payload = _profile_payload(_csrf(invalid_page), version=2)
    invalid_payload["salary_minimum"] = "500000"
    invalid_payload["salary_maximum"] = "100000"
    invalid = client.post("/profile/edit", data=invalid_payload)
    assert invalid.status_code == 400
    assert "Максимальная зарплата" in invalid.get_data(as_text=True)

    without_csrf = client.post("/profile/edit", data={"expected_version": "2"})
    assert without_csrf.status_code == 400


def test_profile_history_is_owner_scoped(app_module, client):
    first_email = f"profile-owner-a-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=first_email)
    page = client.get("/profile/edit")
    client.post(
        "/profile/edit",
        data=_profile_payload(_csrf(page)),
        follow_redirects=False,
    )
    logout_page = client.get("/dashboard")
    client.post(
        "/auth/logout",
        data={"csrf_token": _csrf(logout_page)},
        follow_redirects=False,
    )

    second_email = f"profile-owner-b-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=second_email)
    assert client.get("/profile/history/1").status_code == 404
    assert "Backend engineer" not in client.get("/profile").get_data(as_text=True)

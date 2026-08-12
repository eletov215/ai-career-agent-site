from __future__ import annotations

import html
from io import BytesIO
import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

pytest.importorskip("flask")

from services.email_delivery import MemoryAuthEmailSender


def _csrf(response) -> str:
    match = re.search(
        r'<meta name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return html.unescape(match.group(1))


def _hidden(response, name: str) -> str:
    match = re.search(
        rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"',
        response.get_data(as_text=True),
    )
    assert match, f"missing hidden field {name}"
    return html.unescape(match.group(1))


def _register_verify_login(app_module, client, *, email: str) -> None:
    password = "Resume import route password 42!"
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    register_page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(register_page),
            "display_name": "Resume Import Route",
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
            "password": password,
            "next": "/profile/import",
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302


def _logout(client) -> None:
    dashboard = client.get("/dashboard")
    response = client.post(
        "/auth/logout",
        data={"csrf_token": _csrf(dashboard)},
        follow_redirects=False,
    )
    assert response.status_code == 302


def _text_pdf(lines: list[str]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    commands = ["BT /F1 11 Tf 14 TL 72 720 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("T*")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    content = StreamObject()
    content._data = " ".join(commands).encode("latin-1")
    page[NameObject("/Contents")] = writer._add_object(content)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _resume_pdf() -> bytes:
    return _text_pdf(
        [
            "Jane Doe",
            "Backend Engineer",
            "jane.doe@example.test",
            "Location: Minsk, Belarus",
            "Summary",
            "Backend engineer building reliable APIs.",
            "Skills",
            "Python, SQL, PostgreSQL, Docker",
            "Work Experience",
            "Example Labs",
            "Backend Engineer",
            "January 2022 - present",
            "Built REST APIs and improved reliability.",
            "Education",
            "Example University",
            "Bachelor",
            "Computer Science",
            "2014 - 2018",
            "Languages",
            "English B2",
            "Russian native",
        ]
    )


def _confirmation_payload(review_response, *, headline: str = "Backend Engineer") -> dict[str, str]:
    return {
        "csrf_token": _csrf(review_response),
        "import_token": _hidden(review_response, "import_token"),
        "expected_version": _hidden(review_response, "expected_version"),
        "headline": headline,
        "summary": "Reviewed profile facts.",
        "contact_email": "jane.doe@example.test",
        "target_roles": "Backend Engineer",
        "current_location": "Minsk, Belarus",
        "relocation": "consider",
        "salary_period": "month",
        "salary_tax_mode": "unspecified",
        "skill_name": "Python",
        "skill_level": "unspecified",
        "employment_company": "Example Labs",
        "employment_position": "Backend Engineer",
        "employment_start": "2022-01",
        "employment_end": "",
        "employment_current": "1",
        "employment_description": "Built REST APIs.",
        "achievement_title": "",
        "achievement_year": "",
        "achievement_description": "",
        "education_institution": "Example University",
        "education_degree": "Bachelor",
        "education_field": "Computer Science",
        "education_start_year": "2014",
        "education_end_year": "2018",
        "education_description": "",
        "language_name": "English",
        "language_level": "b2",
    }


def test_resume_import_routes_require_first_party_session(client):
    for path in ("/profile/import", "/profile/import/confirm"):
        response = client.get(path, follow_redirects=False) if path.endswith("import") else client.post(path, follow_redirects=False)
        assert response.status_code in {302, 400}
        if response.status_code == 302:
            assert "/auth/login" in response.headers["Location"]


def test_upload_prepares_editable_review_without_persisting_and_confirm_creates_import_version(app_module, client):
    email = f"prof002-route-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)

    upload_page = client.get("/profile/import")
    assert upload_page.status_code == 200
    assert "ничего не сохраним" in upload_page.get_data(as_text=True)
    review = client.post(
        "/profile/import",
        data={
            "csrf_token": _csrf(upload_page),
            "resume": (BytesIO(_resume_pdf()), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    body = review.get_data(as_text=True)
    assert review.status_code == 200
    assert "Проверка импорта резюме" in body
    assert "Предложения готовы к проверке" in body
    assert "Backend" in body
    assert _hidden(review, "import_token")

    # Extraction and review alone must not create canonical facts.
    profile_before = client.get("/profile")
    assert "Профиль ещё не создан" in profile_before.get_data(as_text=True)

    confirmed = client.post(
        "/profile/import/confirm",
        data=_confirmation_payload(review),
        follow_redirects=False,
    )
    assert confirmed.status_code == 302
    assert confirmed.headers["Location"].endswith("/profile")

    profile = client.get("/profile")
    assert "Backend Engineer" in profile.get_data(as_text=True)
    history = client.get("/profile/history")
    history_body = history.get_data(as_text=True)
    assert "Версия 1" in history_body
    assert "Импорт резюме" in history_body
    version = client.get("/profile/history/1")
    version_body = version.get_data(as_text=True)
    assert "Источник версии" in version_body
    assert "Импорт резюме" in version_body
    assert "deterministic-text-v1" in version_body


def test_import_review_token_is_owner_bound(app_module, client):
    first_email = f"prof002-owner-a-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=first_email)
    page = client.get("/profile/import")
    review = client.post(
        "/profile/import",
        data={
            "csrf_token": _csrf(page),
            "resume": (BytesIO(_resume_pdf()), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    payload = _confirmation_payload(review)

    _logout(client)
    second_email = f"prof002-owner-b-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=second_email)
    second_page = client.get("/profile/import")
    payload["csrf_token"] = _csrf(second_page)
    rejected = client.post("/profile/import/confirm", data=payload)
    assert rejected.status_code == 400
    assert "другому аккаунту" in rejected.get_data(as_text=True)
    assert "Профиль ещё не создан" in client.get("/profile").get_data(as_text=True)


def test_import_confirmation_rejects_stale_profile_version(app_module, client):
    email = f"prof002-stale-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)
    page = client.get("/profile/import")
    review = client.post(
        "/profile/import",
        data={
            "csrf_token": _csrf(page),
            "resume": (BytesIO(_resume_pdf()), "resume.pdf"),
        },
        content_type="multipart/form-data",
    )
    stale_payload = _confirmation_payload(review)

    edit = client.get("/profile/edit")
    manual = client.post(
        "/profile/edit",
        data={
            "csrf_token": _csrf(edit),
            "expected_version": "0",
            "headline": "Manual change",
            "relocation": "consider",
            "salary_period": "month",
            "salary_tax_mode": "unspecified",
        },
        follow_redirects=False,
    )
    assert manual.status_code == 302

    current_page = client.get("/profile/import")
    stale_payload["csrf_token"] = _csrf(current_page)
    rejected = client.post("/profile/import/confirm", data=stale_payload)
    assert rejected.status_code == 409
    assert "изменён в другой сессии" in rejected.get_data(as_text=True)
    assert "Manual change" in client.get("/profile").get_data(as_text=True)


def test_import_rejects_non_pdf_and_image_only_pdf(app_module, client):
    email = f"prof002-invalid-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)
    page = client.get("/profile/import")
    non_pdf = client.post(
        "/profile/import",
        data={
            "csrf_token": _csrf(page),
            "resume": (BytesIO(b"not-a-pdf"), "resume.txt"),
        },
        content_type="multipart/form-data",
    )
    assert non_pdf.status_code == 400
    assert "только файлы PDF" in non_pdf.get_data(as_text=True)

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    retry_page = client.get("/profile/import")
    blank = client.post(
        "/profile/import",
        data={
            "csrf_token": _csrf(retry_page),
            "resume": (BytesIO(buffer.getvalue()), "scan.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert blank.status_code == 400
    assert "не найден текст" in blank.get_data(as_text=True)

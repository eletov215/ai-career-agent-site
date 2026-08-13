from __future__ import annotations

import html
from io import BytesIO
import json
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


def _register_verify_login(app_module, client, *, email: str, next_path: str = "/resumes") -> None:
    password = "Resume draft route password 42!"
    sender = app_module.AUTH_EMAIL_SENDER
    assert isinstance(sender, MemoryAuthEmailSender)
    sender.clear()
    register_page = client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": _csrf(register_page),
            "display_name": "Resume Draft Route",
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
            "next": next_path,
        },
        follow_redirects=False,
    )
    assert logged_in.status_code == 302


def _login(client, *, email: str, next_path: str = "/resumes") -> None:
    login_page = client.get("/auth/login")
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": _csrf(login_page),
            "email": email,
            "password": "Resume draft route password 42!",
            "next": next_path,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302


def _draft_id(location: str) -> str:
    match = re.search(r"/resume-builder/([0-9a-f-]{36})", location)
    assert match
    return match.group(1)


def _builder_initial_state(response) -> dict:
    body = response.get_data(as_text=True)
    match = re.search(
        r'id="resumeBuilderInitialState">(.*?)</script>',
        body,
        flags=re.DOTALL,
    )
    assert match
    return json.loads(html.unescape(match.group(1)))


def _state(*, role: str, photo_asset_id=None) -> dict:
    return {
        "schemaVersion": 1,
        "index": 2,
        "answers": {"name": "Resume Draft Route", "role": role},
        "messages": [
            {"type": "ai", "text": "Как вас зовут?"},
            {"type": "user", "text": "Resume Draft Route"},
        ],
        "photoAssetId": photo_asset_id,
        "universityLogoAssetId": None,
        "universityLogoFor": "",
        "universityResolvedName": "",
    }


def test_resume_draft_pages_require_first_party_session(client):
    for path in ("/resumes", "/resume-builder", "/resume-builder/not-a-draft"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_server_draft_autosaves_versions_restores_and_is_visible_on_another_device(
    app_module, client
):
    email = f"prof003-route-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)

    library = client.get("/resumes")
    created = client.post(
        "/resumes/new",
        data={
            "csrf_token": _csrf(library),
            "source": "blank",
            "title": "Backend resume",
        },
        follow_redirects=False,
    )
    assert created.status_code == 302
    draft_id = _draft_id(created.headers["Location"])

    builder = client.get(created.headers["Location"])
    body = builder.get_data(as_text=True)
    assert builder.status_code == 200
    assert "Черновик синхронизирован" in body
    assert "Сохранить версию" in body
    assert "localStorage.setItem" not in body
    assert _builder_initial_state(builder)["answers"]["name"] == "Resume Draft Route"

    token = _csrf(builder)
    saved = client.put(
        f"/api/resume-drafts/{draft_id}",
        json={"expected_revision": 1, "state": _state(role="Backend Engineer")},
        headers={"X-CSRF-Token": token},
    )
    assert saved.status_code == 200
    saved_json = saved.get_json()
    assert saved_json["ok"] is True
    assert saved_json["changed"] is True
    assert saved_json["revision"] == 2

    stale = client.put(
        f"/api/resume-drafts/{draft_id}",
        json={"expected_revision": 1, "state": _state(role="Stale overwrite")},
        headers={"X-CSRF-Token": token},
    )
    assert stale.status_code == 409

    checkpoint = client.post(
        f"/api/resume-drafts/{draft_id}/checkpoint",
        json={"expected_revision": 2},
        headers={"X-CSRF-Token": token},
    )
    assert checkpoint.status_code == 200
    assert checkpoint.get_json()["version"] == 1

    changed = client.put(
        f"/api/resume-drafts/{draft_id}",
        json={"expected_revision": 2, "state": _state(role="Product Engineer")},
        headers={"X-CSRF-Token": token},
    )
    assert changed.status_code == 200
    assert changed.get_json()["revision"] == 3
    checkpoint_2 = client.post(
        f"/api/resume-drafts/{draft_id}/checkpoint",
        json={"expected_revision": 3},
        headers={"X-CSRF-Token": token},
    )
    assert checkpoint_2.get_json()["version"] == 2

    history = client.get(f"/resumes/{draft_id}/history")
    history_body = history.get_data(as_text=True)
    assert history.status_code == 200
    assert "Версия 1" in history_body
    assert "Версия 2" in history_body

    version_page = client.get(f"/resumes/{draft_id}/history/1")
    assert version_page.status_code == 200
    assert "Backend Engineer" in version_page.get_data(as_text=True)

    restore_page = client.get(f"/resumes/{draft_id}/history")
    restored = client.post(
        f"/resumes/{draft_id}/history/1/restore",
        data={"csrf_token": _csrf(restore_page), "expected_revision": "3"},
        follow_redirects=False,
    )
    assert restored.status_code == 302
    restored_builder = client.get(restored.headers["Location"])
    restored_state = _builder_initial_state(restored_builder)
    assert restored_state["answers"]["role"] == "Backend Engineer"

    # A second browser session sees the same server-owned draft after login.
    other_device = app_module.app.test_client()
    _login(other_device, email=email, next_path=f"/resume-builder/{draft_id}")
    second_builder = other_device.get(f"/resume-builder/{draft_id}")
    assert second_builder.status_code == 200
    assert _builder_initial_state(second_builder)["answers"]["role"] == "Backend Engineer"


def test_asset_upload_uses_upload_limit_and_is_owner_scoped(app_module, client):
    email = f"prof003-asset-a-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)
    library = client.get("/resumes")
    created = client.post(
        "/resumes/new",
        data={"csrf_token": _csrf(library), "source": "blank"},
        follow_redirects=False,
    )
    draft_id = _draft_id(created.headers["Location"])
    builder = client.get(created.headers["Location"])
    token = _csrf(builder)

    # Deliberately larger than the generic 256 KiB request cap, but below the
    # PROF-003 processed-asset cap. The route-specific upload classification
    # must allow it through to the service boundary.
    payload = b"\x89PNG\r\n\x1a\n" + b"x" * (320 * 1024)
    uploaded = client.post(
        f"/api/resume-drafts/{draft_id}/assets",
        data={
            "kind": "photo",
            "asset": (BytesIO(payload), "photo.png", "image/png"),
        },
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    asset_id = uploaded.get_json()["asset_id"]
    assert client.get(f"/resumes/assets/{asset_id}").status_code == 200

    second_client = app_module.app.test_client()
    second_email = f"prof003-asset-b-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, second_client, email=second_email)
    assert second_client.get(f"/resumes/assets/{asset_id}").status_code == 404


def test_pdf_export_metadata_is_recorded_against_current_version(app_module, client):
    email = f"prof003-export-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=email)
    library = client.get("/resumes")
    created = client.post(
        "/resumes/new",
        data={"csrf_token": _csrf(library), "source": "blank"},
        follow_redirects=False,
    )
    draft_id = _draft_id(created.headers["Location"])
    builder = client.get(created.headers["Location"])
    token = _csrf(builder)
    saved = client.put(
        f"/api/resume-drafts/{draft_id}",
        json={"expected_revision": 1, "state": _state(role="Data Engineer")},
        headers={"X-CSRF-Token": token},
    )
    assert saved.status_code == 200

    exported = client.post(
        f"/api/resume-drafts/{draft_id}/exports",
        json={
            "expected_revision": 2,
            "page_count": 2,
            "byte_size": 72_000,
            "pdf_sha256": "a" * 64,
            "file_name": "data-engineer-resume.pdf",
        },
        headers={"X-CSRF-Token": token},
    )
    assert exported.status_code == 200
    result = exported.get_json()
    assert result["ok"] is True
    assert result["version"] == 1
    assert result["version_created"] is True
    assert "Версия 1" in client.get(f"/resumes/{draft_id}/history").get_data(as_text=True)


def test_foreign_user_cannot_open_or_mutate_resume_draft(app_module, client):
    first_email = f"prof003-owner-a-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, client, email=first_email)
    library = client.get("/resumes")
    created = client.post(
        "/resumes/new",
        data={"csrf_token": _csrf(library), "source": "blank"},
        follow_redirects=False,
    )
    draft_id = _draft_id(created.headers["Location"])

    other = app_module.app.test_client()
    second_email = f"prof003-owner-b-{uuid.uuid4().hex}@example.test"
    _register_verify_login(app_module, other, email=second_email)
    page = other.get("/resumes")
    token = _csrf(page)
    assert other.get(f"/resume-builder/{draft_id}").status_code == 404
    assert other.get(f"/resumes/{draft_id}/history").status_code == 404
    rejected = other.put(
        f"/api/resume-drafts/{draft_id}",
        json={"expected_revision": 1, "state": _state(role="Foreign")},
        headers={"X-CSRF-Token": token},
    )
    assert rejected.status_code == 404

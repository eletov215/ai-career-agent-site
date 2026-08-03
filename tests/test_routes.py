from __future__ import annotations

import io

import pytest

pytest.importorskip("flask", reason="Flask is installed from requirements.txt in CI")

from services.base_provider import SearchResult


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/", 200),
        ("/privacy", 200),
        ("/ai-career", 200),
        ("/resume-builder", 200),
        ("/vacancies", 302),
        ("/vacancies/internal", 200),
        ("/health", 200),
        ("/dashboard", 302),
    ],
)
def test_public_route_smoke(client, path, expected_status):
    response = client.get(path)
    assert response.status_code == expected_status


def test_vacancies_redirect_keeps_current_behavior(client):
    response = client.get("/vacancies")
    assert response.headers["Location"].endswith("/ai-career")


def test_resume_preview_validation_does_not_require_network(client):
    missing = client.post("/api/resume/preview")
    wrong_extension = client.post(
        "/api/resume/preview",
        data={"resume": (io.BytesIO(b"text"), "resume.txt")},
        content_type="multipart/form-data",
    )
    invalid_pdf = client.post(
        "/api/resume/preview",
        data={"resume": (io.BytesIO(b"not-pdf"), "resume.pdf")},
        content_type="multipart/form-data",
    )

    assert missing.status_code == 400
    assert wrong_extension.status_code == 400
    assert invalid_pdf.status_code == 400


def test_university_logo_rejects_short_name_before_http(client):
    response = client.post("/api/university/logo", json={"name": "A"})
    assert response.status_code == 400


def test_debug_and_sync_endpoints_have_baseline_access_controls(client):
    assert client.get("/debug/hh").status_code == 404
    assert client.post("/sync/trudvsem").status_code == 401


def test_background_worker_is_disabled_in_test_environment(app_module, client):
    assert app_module.TRUDVSEM_SYNC_ENABLED is False
    client.get("/")
    assert app_module.TRUDVSEM_SYNC_THREAD is None


def test_one_provider_failure_does_not_hide_another_provider_result(
    app_module,
    client,
    monkeypatch,
):
    class WorkingProvider:
        def search(self, *, filters, page=0):
            return SearchResult(
                items=[
                    {
                        "external_id": "reed-1",
                        "source": "reed",
                        "source_title": "Reed.co.uk",
                        "title": "Visible test vacancy",
                        "company": "Test Company",
                        "published_at": "2026-08-03T08:00:00Z",
                        "url": "https://example.test/vacancy",
                    }
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

    class FailingProvider:
        def search(self, *, filters, page=0):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(app_module, "REED_API_KEY", "test-reed-key")
    monkeypatch.setattr(app_module, "HH_APP_TOKEN", "test-hh-token")
    monkeypatch.setattr(app_module, "ReedProvider", lambda *args, **kwargs: WorkingProvider())
    monkeypatch.setattr(app_module, "HeadHunterProvider", lambda *args, **kwargs: FailingProvider())

    response = client.get(
        "/vacancies/internal?search=1&source=reed&source=hh&keyword=python"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Visible test vacancy" in body
    assert "Один из источников временно не смог выполнить поиск" in body
    assert "provider unavailable" not in body

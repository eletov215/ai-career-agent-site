from __future__ import annotations

import io
import re

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
        ("/vacancies", 200),
        ("/vacancies/internal", 308),
        ("/health", 200),
        ("/health/search-dedup", 200),
        ("/dashboard", 302),
    ],
)
def test_public_route_smoke(client, path, expected_status):
    response = client.get(path)
    assert response.status_code == expected_status


def test_vacancies_is_canonical_and_legacy_route_preserves_query(client):
    canonical = client.get("/vacancies")
    body = canonical.get_data(as_text=True)

    assert canonical.status_code == 200
    assert 'rel="canonical"' in body
    assert 'href="http://localhost/vacancies"' in body

    query = (
        "search=1&keyword=Python&source=hh&source=superjob"
        "&snapshot=9368cb00-e7fd-4b67-9276-ea3afcf428ff&page=1"
    )
    legacy = client.get(f"/vacancies/internal?{query}")

    assert legacy.status_code == 308
    assert legacy.headers["Location"].endswith(f"/vacancies?{query}")
    assert legacy.headers["Cache-Control"] == "no-store, max-age=0"
    assert legacy.headers["X-Robots-Tag"] == "noindex"


def test_resume_preview_validation_does_not_require_network(client, csrf_token):
    headers = {"X-CSRF-Token": csrf_token}
    missing = client.post("/api/resume/preview", headers=headers)
    wrong_extension = client.post(
        "/api/resume/preview",
        data={"resume": (io.BytesIO(b"text"), "resume.txt")},
        content_type="multipart/form-data",
        headers=headers,
    )
    invalid_pdf = client.post(
        "/api/resume/preview",
        data={"resume": (io.BytesIO(b"not-pdf"), "resume.pdf")},
        content_type="multipart/form-data",
        headers=headers,
    )

    assert missing.status_code == 400
    assert wrong_extension.status_code == 400
    assert invalid_pdf.status_code == 400


def test_university_logo_rejects_short_name_before_http(client, csrf_token):
    response = client.post(
        "/api/university/logo",
        json={"name": "A"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 400


def test_debug_and_sync_endpoints_have_baseline_access_controls(
    client,
    diagnostics_headers,
):
    assert client.get("/debug/hh").status_code == 404
    assert client.get("/debug/trudvsem").status_code == 404
    assert client.get("/trudvsem/status").status_code == 404
    assert client.get("/trudvsem/status", headers=diagnostics_headers).status_code == 200
    assert client.post("/sync/trudvsem").status_code == 401


def test_application_uses_explicit_test_configuration(app_module):
    assert app_module.SETTINGS.is_test is True
    assert app_module.app.config["APP_ENV"] == "test"
    assert app_module.app.config["TESTING"] is True
    assert app_module.SETTINGS.hh_app_token is None
    assert app_module.SETTINGS.reed_api_key is None
    assert app_module.SETTINGS.csrf_enabled is True
    assert app_module.SETTINGS.rate_limit_enabled is True


def test_background_worker_is_disabled_in_test_environment(app_module, client):
    assert app_module.TRUDVSEM_SYNC_ENABLED is False
    client.get("/")
    assert not hasattr(app_module, "TRUDVSEM_SYNC_THREAD")
    assert not hasattr(app_module, "TRUDVSEM_SYNC_EVENT")
    assert not hasattr(app_module, "TRUDVSEM_SYNC_STATE")
    assert app_module.STORAGE.sync_workers.latest("trudvsem") is None


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
                        "title": "Python Visible test vacancy",
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
        "/vacancies?search=1&source=reed&source=hh&keyword=python"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Visible test vacancy" in body
    assert "Часть источников работает с ограничениями" in body
    assert "Работает с ограничениями" in body
    assert 'data-source-state="degraded"' in body
    assert "provider unavailable" not in body




def test_superjob_source_is_available_without_oauth_account(app_module, client, monkeypatch):
    class PublicSuperJobProvider:
        def search(self, *, filters, page=0):
            return SearchResult(
                items=[
                    {
                        "external_id": "sj-public-1",
                        "source": "superjob",
                        "source_title": "SuperJob",
                        "title": "Python public SuperJob vacancy",
                        "company": "ACME",
                        "published_at": "2026-08-09T08:00:00Z",
                        "url": "https://sj.example.test/1",
                    }
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

    monkeypatch.setattr(app_module, "CLIENT_SECRET", "test-superjob-app-secret")
    monkeypatch.setattr(app_module, "SuperJobProvider", lambda *args, **kwargs: PublicSuperJobProvider())

    with client.session_transaction() as browser_session:
        browser_session.pop("superjob_user_id", None)

    response = client.get(
        "/vacancies?search=1&source=superjob&keyword=python"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Python public SuperJob vacancy" in body
    assert "SuperJob не подключён" not in body


def test_unconfigured_source_is_excluded_with_safe_user_message(
    app_module,
    client,
    monkeypatch,
):
    called = False

    class ReedShouldNotRun:
        def search(self, *, filters, page=0):
            nonlocal called
            called = True
            raise AssertionError("unconfigured provider must not run")

    monkeypatch.setattr(app_module, "REED_API_KEY", None)
    monkeypatch.setattr(
        app_module,
        "ReedProvider",
        lambda *args, **kwargs: ReedShouldNotRun(),
    )

    response = client.get(
        "/vacancies?search=1&source=reed&keyword=python"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert called is False
    assert "Недоступные сейчас источники не включены в поиск: Reed.co.uk." in body
    assert "Временно недоступен" in body
    assert "REED_API_KEY" not in body
    assert "Render" not in body


def test_cross_source_duplicates_render_once_with_all_source_links(
    app_module,
    client,
    monkeypatch,
):
    from datetime import datetime, timezone

    published = datetime.now(timezone.utc).isoformat()

    class HHProvider:
        def search(self, *, filters, page=0):
            return SearchResult(
                items=[
                    {
                        "external_id": "hh-dedup-1",
                        "source": "hh",
                        "source_title": "HeadHunter",
                        "title": "SEARCH002 Unique Python backend developer",
                        "company": "ООО ACME",
                        "location": "Москва",
                        "work_format": "remote",
                        "employment_code": "full",
                        "experience_code": "between_1_and_3",
                        "salary_from": 180000,
                        "salary_to": 240000,
                        "currency": "RUB",
                        "description": "Python API PostgreSQL integrations",
                        "requirements": "Python SQL REST",
                        "published_at": published,
                        "url": "https://hh.example.test/dedup-1",
                        "source_status": "active",
                    }
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

    class ReedProviderFake:
        def search(self, *, filters, page=0):
            return SearchResult(
                items=[
                    {
                        "external_id": "reed-dedup-1",
                        "source": "reed",
                        "source_title": "Reed.co.uk",
                        "title": "SEARCH002 Unique Python backend-разработчик",
                        "company": "ACME",
                        "location": "Россия",
                        "work_format": "remote",
                        "employment_code": "full",
                        "experience_code": "between_1_and_3",
                        "salary_from": 185000,
                        "salary_to": 235000,
                        "currency": "RUB",
                        "description": "Python API PostgreSQL integrations",
                        "requirements": "Python SQL REST",
                        "published_at": published,
                        "url": "https://reed.example.test/dedup-1",
                        "source_status": "active",
                    }
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

    monkeypatch.setattr(app_module, "REED_API_KEY", "test-reed-key")
    monkeypatch.setattr(app_module, "HH_APP_TOKEN", "test-hh-token")
    monkeypatch.setattr(app_module, "ReedProvider", lambda *args, **kwargs: ReedProviderFake())
    monkeypatch.setattr(app_module, "HeadHunterProvider", lambda *args, **kwargs: HHProvider())

    response = client.get(
        "/vacancies?search=1&source=reed&source=hh&keyword=SEARCH002"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert body.count("SEARCH002 Unique Python backend") == 1
    assert "2 источника" in body
    assert "Все площадки" in body
    assert "https://hh.example.test/dedup-1" in body
    assert "https://reed.example.test/dedup-1" in body
    assert "Объединено повторов: 1" in body

    status_response = client.get("/health/search-dedup")
    status_payload = status_response.get_json()
    assert status_response.status_code == 200
    assert status_payload["dedup"]["available"] is True
    assert status_payload["dedup"]["stats"]["input_count"] == 2
    assert status_payload["dedup"]["stats"]["output_count"] == 1
    assert status_payload["dedup"]["stats"]["cross_source_duplicate_count"] == 1
    assert status_payload["dedup"]["stats"]["cross_source_groups"] == 1
    assert status_payload["dedup"]["candidate_counts_by_source"] == {"hh": 1, "reed": 1}


def test_sqlalchemy_account_storage_round_trip(app_module):
    from flask import session

    app_module.save_account(
        {"id": 101, "name": "Test SuperJob", "email": "sj@example.test"},
        {
            "access_token": "superjob-access",
            "refresh_token": "superjob-refresh",
            "expires_in": 3600,
        },
    )
    app_module.save_hh_account(
        {
            "id": "hh-101",
            "first_name": "Test",
            "last_name": "HH",
            "email": "hh@example.test",
        },
        {
            "access_token": "hh-access",
            "refresh_token": "hh-refresh",
            "expires_in": 3600,
        },
    )

    # account() and hh_account() intentionally read Flask's request-local
    # session, so the direct helper check must run inside a request context.
    with app_module.app.test_request_context("/"):
        session["superjob_user_id"] = 101
        session["hh_user_id"] = "hh-101"

        superjob = app_module.account()
        headhunter = app_module.hh_account()

    assert superjob["name"] == "Test SuperJob"
    assert headhunter["first_name"] == "Test"
    assert app_module.dec(superjob["access_token"]) == "superjob-access"
    assert app_module.dec(headhunter["access_token"]) == "hh-access"


def test_health_reports_migrated_database_without_connection_url(client):
    from database import CURRENT_REVISION

    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["database"]["ok"] is True
    assert payload["database"]["backend"] == "sqlite"
    assert payload["database"]["revision"] == CURRENT_REVISION
    assert "sqlite:///" not in response.get_data(as_text=True)


def test_trudvsem_status_includes_latest_persisted_sync_run(
    app_module,
    client,
    diagnostics_headers,
):
    run = app_module.SYNC_RUNS.start(
        source="trudvsem",
        trigger="route-test",
        target=10,
    )
    app_module.SYNC_RUNS.finish(
        run.id,
        status="succeeded",
        processed=10,
        saved=8,
        cursor="10",
    )

    response = client.get("/trudvsem/status", headers=diagnostics_headers)
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["persisted_run"]["id"] == run.id
    assert payload["persisted_run"]["status"] == "succeeded"
    assert payload["persisted_run"]["saved"] == 8


def test_public_trudvsem_status_is_sanitized(app_module, client):
    run = app_module.SYNC_RUNS.start(
        source="trudvsem",
        trigger="sanitization-test",
        target=1,
    )
    app_module.SYNC_RUNS.finish(
        run.id,
        status="failed",
        processed=0,
        saved=0,
        error_type="ProviderPrivateError",
        error_message="private provider exception",
    )

    response = client.get("/api/sources/trudvsem/status")
    payload = response.get_json()

    assert response.status_code == 200
    assert set(payload) == {
        "available",
        "cache_age_seconds",
        "cached_total",
        "progress_percent",
        "queued",
        "running",
        "source",
    }
    assert "private provider exception" not in response.get_data(as_text=True)
    assert "persisted_run" not in payload


def test_csrf_protects_form_and_json_posts(client, csrf_token):
    missing = client.post("/api/resume/preview")
    accepted = client.post(
        "/api/resume/preview",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert missing.status_code == 400
    assert missing.get_json()["error"] == "Обновите страницу и повторите действие."
    assert accepted.status_code == 400
    assert accepted.get_json()["error"] == "Выберите PDF-файл с резюме."


def test_security_headers_and_csrf_nonce_are_present(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    csp = response.headers["Content-Security-Policy"]

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert "frame-ancestors 'none'" in csp
    assert "script-src-attr 'none'" in csp
    assert "'unsafe-inline'" not in csp.split("style-src", 1)[0]
    assert 'meta name="csrf-token"' in body

    nonce_match = re.search(r'<script nonce="([^"]+)"', body)
    assert nonce_match, "Rendered page did not include a CSP nonce"
    assert f"'nonce-{nonce_match.group(1)}'" in csp


def test_session_cookie_is_http_only_and_same_site(client):
    response = client.get("/")
    cookie = response.headers.get("Set-Cookie", "")

    assert cookie.startswith("aca_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie  # test mode intentionally uses HTTP


def test_logout_requires_post_and_csrf(client, csrf_token):
    with client.session_transaction() as browser_session:
        browser_session["hh_user_id"] = "hh-test"

    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 400

    response = client.post(
        "/logout",
        data={"csrf_token": csrf_token},
    )
    assert response.status_code == 302
    with client.session_transaction() as browser_session:
        assert "hh_user_id" not in browser_session


def test_rate_limit_blocks_repeated_resume_preview_requests(client, csrf_token):
    headers = {"X-CSRF-Token": csrf_token}
    statuses = [
        client.post("/api/resume/preview", headers=headers).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [400] * 10
    assert statuses[10] == 429


def test_oauth_provider_error_requires_valid_state_and_is_not_reflected(client):
    start = client.get("/oauth/hh/login")
    assert start.status_code == 302
    with client.session_transaction() as browser_session:
        state = browser_session["hh_oauth_state"]

    response = client.get(
        f"/oauth/hh/callback?error=secret-provider-detail&state={state}"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "secret-provider-detail" not in body
    assert "Подключение HeadHunter было отменено" in body
    with client.session_transaction() as browser_session:
        assert "hh_oauth_state" not in browser_session


def test_superjob_provider_error_requires_valid_state_and_is_not_reflected(client):
    start = client.get("/oauth/superjob/login")
    assert start.status_code == 302
    with client.session_transaction() as browser_session:
        state = browser_session["superjob_oauth_state"]

    response = client.get(
        f"/oauth/superjob/callback?error=secret-provider-detail&state={state}"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "secret-provider-detail" not in body
    assert "Подключение SuperJob было отменено" in body
    with client.session_transaction() as browser_session:
        assert "superjob_oauth_state" not in browser_session


def test_oauth_provider_error_with_invalid_state_is_rejected(client):
    response = client.get(
        "/oauth/hh/callback?error=provider-cancelled&state=invalid"
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "Ошибка безопасности" in body
    assert "Подключение HeadHunter было отменено" not in body


def test_token_refresh_network_errors_do_not_expose_sensitive_values(
    app_module,
    monkeypatch,
):
    def fail_request(*_args, **_kwargs):
        raise app_module.requests.Timeout(
            "request failed for refresh-token-secret and client-secret"
        )

    monkeypatch.setattr(app_module.requests, "get", fail_request)
    superjob_row = {
        "expires_at": 1,
        "refresh_token": app_module.enc("refresh-token-secret"),
        "profile_json": '{"id": 101}',
        "access_token": app_module.enc("access-token-secret"),
    }
    with pytest.raises(RuntimeError) as superjob_error:
        app_module.valid_token(superjob_row)

    monkeypatch.setattr(app_module.requests, "post", fail_request)
    hh_row = {
        "expires_at": 1,
        "refresh_token": app_module.enc("hh-refresh-token-secret"),
        "profile_json": '{"id": "hh-101"}',
        "access_token": app_module.enc("hh-access-token-secret"),
    }
    with pytest.raises(RuntimeError) as hh_error:
        app_module.valid_hh_token(hh_row)

    combined = f"{superjob_error.value} {hh_error.value}"
    assert "refresh-token-secret" not in combined
    assert "client-secret" not in combined
    assert "Подключите" in combined


def test_unknown_route_uses_neutral_error_page(client):
    response = client.get("/missing-page")
    body = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Страница не найдена" in body
    assert "The requested URL was not found" not in body


def test_untrusted_host_is_rejected_without_reflection(client):
    response = client.get("/", headers={"Host": "evil.example"})
    body = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "evil.example" not in body
    assert "Адрес запроса не разрешён" in body


def test_manual_refresh_requires_csrf_outside_production(
    app_module,
    client,
    csrf_token,
    monkeypatch,
):
    monkeypatch.setattr(
        app_module,
        "request_trudvsem_sync",
        lambda **_kwargs: None,
    )

    assert client.post("/trudvsem/refresh").status_code == 400
    accepted = client.post(
        "/trudvsem/refresh",
        data={"csrf_token": csrf_token, "source": "trudvsem"},
    )
    assert accepted.status_code == 302


def test_machine_sync_endpoint_only_queues_external_job(
    app_module,
    client,
    monkeypatch,
):
    queued = app_module.SYNC_RUNS.enqueue(
        source="trudvsem",
        trigger="route-fixture",
        target=3,
    )
    monkeypatch.setattr(app_module, "SYNC_SECRET", "test-sync-secret")
    monkeypatch.setattr(
        app_module,
        "request_trudvsem_sync",
        lambda **_kwargs: queued,
    )

    response = client.post(
        "/sync/trudvsem",
        headers={"X-Sync-Secret": "test-sync-secret"},
    )
    payload = response.get_json()

    assert response.status_code == 202
    assert payload["run_id"] == queued.id
    assert payload["status"] == "queued"
    assert payload["message"] == "sync job queued for external worker"


def test_oauth_state_is_single_use_and_expires(app_module, monkeypatch):
    from flask import session

    monkeypatch.setattr(app_module.time, "time", lambda: 1_000)
    with app_module.app.test_request_context("/"):
        state = app_module._remember_oauth_state("hh")
        assert session["hh_oauth_state"] == state
        assert app_module._consume_oauth_state("hh", state) is True
        assert app_module._consume_oauth_state("hh", state) is False

    monkeypatch.setattr(app_module.time, "time", lambda: 2_000)
    with app_module.app.test_request_context("/"):
        expired_state = app_module._remember_oauth_state("superjob")
        session["superjob_oauth_state_issued_at"] = 1_000
        assert app_module._consume_oauth_state("superjob", expired_state) is False


def test_uploaded_filename_is_sanitized(app_module):
    assert app_module._safe_upload_filename("../../My Resume.pdf") == "My_Resume.pdf"
    assert app_module._safe_upload_filename("../..") == "resume.pdf"


def test_oversized_resume_is_rejected_before_pdf_parsing(client, csrf_token):
    oversized = b"%PDF" + (b"x" * (8 * 1024 * 1024 + 1))
    response = client.post(
        "/api/resume/preview",
        data={"resume": (io.BytesIO(oversized), "resume.pdf")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 413
    assert "8 МБ" in response.get_json()["error"]


def test_search003_snapshot_pagination_links_and_health_endpoint(
    app_module,
    client,
    monkeypatch,
):
    from datetime import datetime, timedelta, timezone
    from services.search_aggregation import SearchAggregationService

    now = datetime.now(timezone.utc)

    class PagedHHProvider:
        def search(self, *, filters, page=0):
            page_items = []
            for offset in range(2):
                index = page * 2 + offset
                if index >= 4:
                    break
                page_items.append(
                    {
                        "external_id": f"search003-{index}",
                        "source": "hh",
                        "source_title": "HeadHunter",
                        "title": f"SEARCH003 stable role {index}",
                        "company": "Snapshot Test",
                        "location": "Москва",
                        "work_format": "remote",
                        "employment_code": "full",
                        "experience_code": "between_1_and_3",
                        "published_at": (
                            now - timedelta(minutes=index)
                        ).isoformat(),
                        "url": f"https://hh.example.test/search003-{index}",
                        "source_status": "active",
                    }
                )
            return SearchResult(
                items=page_items,
                total=4,
                page=page,
                pages=2,
                has_next=page == 0,
            )

    monkeypatch.setattr(app_module, "HH_APP_TOKEN", "test-hh-token")
    monkeypatch.setattr(
        app_module,
        "HeadHunterProvider",
        lambda *args, **kwargs: PagedHHProvider(),
    )
    monkeypatch.setattr(
        app_module,
        "SEARCH_AGGREGATION",
        SearchAggregationService(
            app_module.STORAGE.search_snapshots,
            page_size=2,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=2,
        ),
    )

    first = client.get(
        "/vacancies?search=1&source=hh&keyword=SEARCH003"
    )
    first_body = first.get_data(as_text=True)
    assert first.status_code == 200
    assert "SEARCH003 stable role 0" in first_body
    assert "SEARCH003 stable role 1" in first_body
    assert "SEARCH003 stable role 2" not in first_body
    snapshot_match = re.search(r"snapshot=([0-9a-f-]{36})", first_body)
    assert snapshot_match
    snapshot_id = snapshot_match.group(1)

    second = client.get(
        "/vacancies?search=1&source=hh&keyword=SEARCH003"
        f"&snapshot={snapshot_id}&page=1"
    )
    second_body = second.get_data(as_text=True)
    assert second.status_code == 200
    assert "SEARCH003 stable role 0" not in second_body
    assert "SEARCH003 stable role 2" in second_body
    assert "SEARCH003 stable role 3" in second_body

    status = client.get(f"/health/search-pagination?snapshot={snapshot_id}")
    payload = status.get_json()
    assert status.status_code == 200
    assert payload["package"] == "SEARCH-003"
    assert payload["snapshot"]["known_unique_total"] == 4
    assert payload["snapshot"]["total_is_exact"] is True
    assert payload["snapshot"]["sources"]["hh"]["fetched_pages"] == 2
    response_text = status.get_data(as_text=True)
    assert "SEARCH003" not in response_text
    assert "keyword" not in response_text

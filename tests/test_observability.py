from __future__ import annotations

import json
import logging

import pytest

pytest.importorskip("flask", reason="Flask is installed from requirements.txt in CI")

from observability import (
    ALERT_DISPATCHER,
    OPS_STATE,
    JsonLogFormatter,
    LogSanitizer,
    OpsErrorHandler,
    provider_operation,
)


def test_log_sanitizer_redacts_configured_and_common_credentials():
    sanitizer = LogSanitizer(["super-secret", "postgresql://user:pass@db/app"])
    text = sanitizer.redact_text(
        "Authorization: Bearer abcdefghijklmnop "
        "access_token=visible super-secret "
        "postgresql://user:pass@db/app "
        "https://api.example.test/search?keyword=private-role&region=private-region"
    )

    assert "super-secret" not in text
    assert "abcdefghijklmnop" not in text
    assert "visible" not in text
    assert "pass@db" not in text
    assert "private-role" not in text
    assert "private-region" not in text
    assert "https://api.example.test/search?[QUERY_REDACTED]" in text
    assert text.count("[REDACTED]") >= 3




def test_log_sanitizer_redacts_sensitive_mapping_values_by_key():
    sanitizer = LogSanitizer()
    payload = sanitizer.redact(
        {
            "password": "not-configured-secret",
            "Authorization": "Basic abcdefghijkl",
            "nested": {"api_key": "another-secret", "safe": "visible"},
        }
    )

    assert payload["password"] == "[REDACTED]"
    assert payload["Authorization"] == "[REDACTED]"
    assert payload["nested"]["api_key"] == "[REDACTED]"
    assert payload["nested"]["safe"] == "visible"


def test_json_formatter_emits_bounded_structured_record_without_secret():
    sanitizer = LogSanitizer(["hidden-value"])
    formatter = JsonLogFormatter(
        sanitizer=sanitizer,
        service_name="career-test",
        environment="test",
        app_version="abc123",
    )
    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failed token=hidden-value",
        args=(),
        exc_info=None,
    )
    record.event = "test_event"
    record.request_id = "request-12345678"

    payload = json.loads(formatter.format(record))

    assert payload["service"] == "career-test"
    assert payload["environment"] == "test"
    assert payload["version"] == "abc123"
    assert payload["event"] == "test_event"
    assert payload["request_id"] == "request-12345678"
    assert "hidden-value" not in payload["message"]


def test_request_id_is_returned_and_valid_incoming_id_is_preserved(client):
    supplied = "client-request-12345678"
    response = client.get("/health/live", headers={"X-Request-ID": supplied})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == supplied
    assert response.get_json()["request_id"] == supplied

    invalid = client.get("/health/live", headers={"X-Request-ID": "bad id"})
    generated = invalid.headers["X-Request-ID"]
    assert generated != "bad id"
    assert len(generated) == 32


def test_liveness_and_readiness_are_secret_free(client):
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.get_json()["status"] == "ok"
    assert ready.status_code == 200
    payload = ready.get_json()
    assert payload["migrations"]["ok"] is True
    assert payload["database"]["ok"] is True
    body = ready.get_data(as_text=True)
    assert "sqlite:///" not in body
    assert "postgresql+psycopg" not in body
    assert "password" not in body.casefold()


def test_readiness_fails_on_revision_mismatch(app_module, client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "database_health",
        lambda _runtime: {
            "ok": True,
            "backend": "sqlite",
            "persistent": False,
            "revision": "old_revision",
        },
    )

    response = client.get("/health/ready")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["migrations"]["ok"] is False


def test_ops_status_is_hidden_and_contains_bounded_metrics(
    client,
    diagnostics_headers,
):
    client.get("/privacy?access_token=do-not-record")
    client.get("/health/live")

    assert client.get("/ops/status").status_code == 404
    response = client.get("/ops/status", headers=diagnostics_headers)
    payload = response.get_json()

    assert response.status_code == 200
    assert "telemetry" in payload
    assert "privacy" in payload["telemetry"]["http"]
    assert "health_live" in payload["telemetry"]["http"]
    assert "do-not-record" not in response.get_data(as_text=True)
    assert "database_url" not in response.get_data(as_text=True).casefold()


def test_provider_metrics_record_success_and_failure():
    OPS_STATE.reset_for_tests()

    with provider_operation("hh", "vacancy_search") as observation:
        observation.status_code = 200
        observation.result_count = 3

    with provider_operation("reed", "vacancy_search") as observation:
        observation.fail("ProviderSearchError", status_code=503)

    snapshot = OPS_STATE.snapshot()
    assert snapshot["providers"]["hh"]["vacancy_search"]["successes"] == 1
    assert snapshot["providers"]["reed"]["vacancy_search"]["failures"] == 1
    assert snapshot["providers"]["reed"]["vacancy_search"]["last_status_code"] == 503


def test_error_handler_records_sanitized_recent_error(monkeypatch):
    sanitizer = LogSanitizer(["private-secret"])
    OPS_STATE.configure(
        type(
            "Settings",
            (),
            {
                "service_name": "test",
                "environment": "test",
                "app_version": "test",
                "ops_alert_webhook_url": None,
            },
        )(),
        sanitizer,
    )
    OPS_STATE.reset_for_tests()
    monkeypatch.setattr(ALERT_DISPATCHER, "minimum_level", logging.CRITICAL)
    handler = OpsErrorHandler(sanitizer)
    record = logging.LogRecord(
        "test.ops",
        logging.ERROR,
        __file__,
        1,
        "failure secret=private-secret",
        (),
        None,
    )

    handler.emit(record)
    recent = OPS_STATE.snapshot()["recent_errors"]

    assert len(recent) == 1
    assert "private-secret" not in recent[0]["message"]


def test_alert_test_endpoint_is_diagnostics_only(
    client,
    diagnostics_headers,
    monkeypatch,
):
    assert client.post("/ops/alerts/test").status_code == 404

    monkeypatch.setattr(ALERT_DISPATCHER, "url", None)
    assert client.post(
        "/ops/alerts/test",
        headers=diagnostics_headers,
    ).status_code == 503

    monkeypatch.setattr(ALERT_DISPATCHER, "url", "https://alerts.example.test/hook")
    monkeypatch.setattr(ALERT_DISPATCHER, "enqueue", lambda _payload: True)
    response = client.post("/ops/alerts/test", headers=diagnostics_headers)

    assert response.status_code == 202
    assert response.get_json()["status"] == "queued"


def test_alert_dispatcher_uses_https_webhook_without_exposing_token(monkeypatch):
    calls = []

    class Response:
        status_code = 202

        def raise_for_status(self):
            return None

    def fake_post(url, *, json, headers, timeout):  # noqa: A002
        calls.append((url, json, headers, timeout))
        return Response()

    monkeypatch.setattr("observability.requests.post", fake_post)
    monkeypatch.setattr(ALERT_DISPATCHER, "url", "https://alerts.example.test/hook")
    monkeypatch.setattr(ALERT_DISPATCHER, "token", "private-alert-token")
    monkeypatch.setattr(ALERT_DISPATCHER, "timeout", 2.5)

    assert ALERT_DISPATCHER.send_now({"event": "test", "message": "safe"}) is True
    assert calls[0][0] == "https://alerts.example.test/hook"
    assert calls[0][1] == {"event": "test", "message": "safe"}
    assert calls[0][2]["Authorization"] == "Bearer private-alert-token"
    assert calls[0][3] == 2.5

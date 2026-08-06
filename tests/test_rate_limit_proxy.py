from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="Flask is installed from requirements.txt in CI")

from security import limiter, rate_limit_client_address, rate_limit_key


def test_forwarded_client_address_is_used_only_when_explicitly_trusted(app_module):
    app = app_module.app
    original = app.config.get("TRUST_PROXY_HEADERS", False)
    try:
        app.config["TRUST_PROXY_HEADERS"] = True
        with app.test_request_context(
            "/",
            headers={
                "CF-Connecting-IP": "203.0.113.17",
                "X-Forwarded-For": "198.51.100.8, 10.0.0.9",
            },
            environ_base={"REMOTE_ADDR": "10.0.0.10"},
        ):
            assert rate_limit_client_address() == "203.0.113.17"
            assert "203.0.113.17" not in rate_limit_key()

        app.config["TRUST_PROXY_HEADERS"] = False
        with app.test_request_context(
            "/",
            headers={
                "CF-Connecting-IP": "203.0.113.17",
                "X-Forwarded-For": "198.51.100.8, 10.0.0.9",
            },
            environ_base={"REMOTE_ADDR": "10.0.0.10"},
        ):
            assert rate_limit_client_address() == "10.0.0.10"
    finally:
        app.config["TRUST_PROXY_HEADERS"] = original


def test_x_forwarded_for_first_address_is_stable_fallback(app_module):
    app = app_module.app
    original = app.config.get("TRUST_PROXY_HEADERS", False)
    try:
        app.config["TRUST_PROXY_HEADERS"] = True
        with app.test_request_context(
            "/",
            headers={
                "CF-Connecting-IP": "not-an-ip",
                "X-Forwarded-For": "198.51.100.23, 10.0.0.4, 10.0.0.5",
            },
            environ_base={"REMOTE_ADDR": "10.0.0.6"},
        ):
            assert rate_limit_client_address() == "198.51.100.23"
    finally:
        app.config["TRUST_PROXY_HEADERS"] = original


def test_rate_limit_probe_reaches_429_when_proxy_hops_rotate(app_module):
    app = app_module.app
    original = app.config.get("TRUST_PROXY_HEADERS", False)
    limiter.reset()
    try:
        app.config["TRUST_PROXY_HEADERS"] = True
        client = app.test_client(use_cookies=False)
        statuses = []
        responses = []
        for index in range(6):
            response = client.get(
                "/api/security/rate-limit-probe",
                headers={
                    "CF-Connecting-IP": "203.0.113.44",
                    "X-Forwarded-For": (
                        f"203.0.113.44, 10.0.0.{index + 1}"
                    ),
                },
                environ_overrides={"REMOTE_ADDR": f"10.1.0.{index + 1}"},
            )
            statuses.append(response.status_code)
            responses.append(response)

        assert statuses[:5] == [200] * 5
        assert statuses[5] == 429
        assert responses[5].headers.get("Retry-After")
        assert responses[5].get_json() == {
            "ok": False,
            "error": "Подождите немного и повторите действие.",
        }
    finally:
        app.config["TRUST_PROXY_HEADERS"] = original
        limiter.reset()


def test_invalid_forwarded_values_fall_back_to_direct_peer(app_module):
    app = app_module.app
    original = app.config.get("TRUST_PROXY_HEADERS", False)
    try:
        app.config["TRUST_PROXY_HEADERS"] = True
        with app.test_request_context(
            "/",
            headers={
                "CF-Connecting-IP": "invalid",
                "X-Forwarded-For": "also-invalid",
            },
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        ):
            assert rate_limit_client_address() == "127.0.0.1"
    finally:
        app.config["TRUST_PROXY_HEADERS"] = original

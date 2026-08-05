from __future__ import annotations

import importlib
import html
import os
import re
import shutil
import tempfile
from pathlib import Path

import pytest
import requests


_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="ai-career-agent-tests-"))

# The configuration layer provides deterministic placeholder credentials only
# in APP_ENV=test. The suite therefore never needs real OAuth or encryption
# secrets. DATA_DIR remains unique per test session and background sync is
# explicitly disabled before app.py is imported.
os.environ["APP_ENV"] = "test"
os.environ["DATA_DIR"] = str(_TEST_DATA_DIR)
os.environ["TRUDVSEM_SYNC_ENABLED"] = "0"
os.environ["TRUDVSEM_REQUEST_ATTEMPTS"] = "1"
os.environ["TRUDVSEM_RETRY_BACKOFF"] = "0.1"
os.environ["DEBUG_HH"] = "0"
os.environ["DEBUG_DIAGNOSTICS"] = "1"
os.environ["RATE_LIMIT_ENABLED"] = "1"

# Remove accidental developer or CI credentials so the route tests prove that
# test mode is self-contained.
for variable in (
    "FLASK_SECRET_KEY",
    "TOKEN_ENCRYPTION_KEY",
    "SUPERJOB_CLIENT_ID",
    "SUPERJOB_CLIENT_SECRET",
    "SUPERJOB_REDIRECT_URI",
    "HH_CLIENT_ID",
    "HH_CLIENT_SECRET",
    "HH_REDIRECT_URI",
    "HH_USER_AGENT",
    "HH_APP_TOKEN",
    "REED_API_KEY",
    "SYNC_SECRET",
    "DIAGNOSTICS_SECRET",
    "DATABASE_URL",
    "TRUSTED_HOSTS",
    "RATELIMIT_STORAGE_URI",
):
    os.environ.pop(variable, None)


@pytest.fixture(autouse=True)
def block_unmocked_http(monkeypatch: pytest.MonkeyPatch):
    """Make accidental network access fail immediately in every test."""

    def blocked_request(self, method, url, *args, **kwargs):  # noqa: ANN001
        raise AssertionError(
            f"External HTTP is forbidden in tests: {method} {url}. "
            "Mock the provider response explicitly."
        )

    monkeypatch.setattr(requests.sessions.Session, "request", blocked_request)


@pytest.fixture(scope="session")
def app_module():
    pytest.importorskip("flask", reason="Flask is installed from requirements.txt in CI")
    from config import load_database_url
    from database import upgrade_database

    database_url, _explicit = load_database_url()
    upgrade_database(database_url)
    module = importlib.import_module("app")
    module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-flask-secret",
    )
    return module


@pytest.fixture()
def client(app_module):
    from security import limiter

    limiter.reset()
    test_client = app_module.app.test_client()
    yield test_client
    limiter.reset()


@pytest.fixture()
def csrf_token(client):
    response = client.get("/")
    match = re.search(
        r'<meta name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, "CSRF token meta tag is missing"
    return html.unescape(match.group(1))


@pytest.fixture()
def diagnostics_headers():
    return {"X-Diagnostics-Secret": "test-diagnostics-secret"}


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
    module = __import__("sys").modules.get("app")
    if module is not None and hasattr(module, "DATABASE"):
        module.DATABASE.dispose()
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)

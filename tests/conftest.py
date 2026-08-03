from __future__ import annotations

import importlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import requests
from cryptography.fernet import Fernet


_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="ai-career-agent-tests-"))

# app.py reads these values during import. They are intentionally fake and are
# defined before any test imports the application module.
os.environ.setdefault("FLASK_SECRET_KEY", "test-only-flask-secret")
os.environ.setdefault("SUPERJOB_CLIENT_ID", "test-superjob-client")
os.environ.setdefault("SUPERJOB_CLIENT_SECRET", "test-superjob-secret")
os.environ.setdefault("SUPERJOB_REDIRECT_URI", "http://localhost/oauth/superjob/callback")
os.environ.setdefault("HH_CLIENT_ID", "test-hh-client")
os.environ.setdefault("HH_CLIENT_SECRET", "test-hh-secret")
os.environ.setdefault("HH_REDIRECT_URI", "http://localhost/oauth/hh/callback")
os.environ.setdefault("HH_USER_AGENT", "AI-Career-Agent-Test/1.0 (tests@example.invalid)")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
os.environ.setdefault("HH_APP_TOKEN", "test-hh-app-token")
os.environ.setdefault("REED_API_KEY", "test-reed-key")
os.environ.setdefault("SYNC_SECRET", "test-sync-secret")
os.environ.setdefault("DATA_DIR", str(_TEST_DATA_DIR))
os.environ.setdefault("TRUDVSEM_SYNC_ENABLED", "0")
os.environ.setdefault("TRUDVSEM_REQUEST_ATTEMPTS", "1")
os.environ.setdefault("TRUDVSEM_RETRY_BACKOFF", "0.1")
os.environ.setdefault("DEBUG_HH", "0")


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
    module = importlib.import_module("app")
    module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-only-flask-secret",
    )
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)

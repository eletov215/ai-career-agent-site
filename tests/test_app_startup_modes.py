from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask", reason="Flask is installed from requirements.txt in CI")


VALID_FERNET_KEY = "yPWPkxw3j4ZWDVBQ-i3kryGBFjd-5Bjg2tDjCNUMciw="
REQUIRED_NAMES = (
    "FLASK_SECRET_KEY",
    "TOKEN_ENCRYPTION_KEY",
    "SUPERJOB_CLIENT_ID",
    "SUPERJOB_CLIENT_SECRET",
    "SUPERJOB_REDIRECT_URI",
    "HH_CLIENT_ID",
    "HH_CLIENT_SECRET",
    "HH_REDIRECT_URI",
    "HH_USER_AGENT",
)


def _base_environment(tmp_path: Path, app_env: str) -> dict[str, str]:
    environment = dict(os.environ)
    for name in REQUIRED_NAMES:
        environment.pop(name, None)

    environment.update(
        {
            "APP_ENV": app_env,
            "DATA_DIR": str(tmp_path),
            "TRUDVSEM_SYNC_ENABLED": "0",
            "TRUDVSEM_REQUEST_ATTEMPTS": "1",
            "TRUDVSEM_RETRY_BACKOFF": "0.1",
            "DEBUG_HH": "0",
        }
    )

    if app_env != "test":
        environment.update(
            {
                "FLASK_SECRET_KEY": f"{app_env}-flask-secret",
                "TOKEN_ENCRYPTION_KEY": VALID_FERNET_KEY,
                "SUPERJOB_CLIENT_ID": f"{app_env}-sj-id",
                "SUPERJOB_CLIENT_SECRET": f"{app_env}-sj-secret",
                "SUPERJOB_REDIRECT_URI": (
                    f"https://example.test/{app_env}/oauth/superjob/callback"
                ),
                "HH_CLIENT_ID": f"{app_env}-hh-id",
                "HH_CLIENT_SECRET": f"{app_env}-hh-secret",
                "HH_REDIRECT_URI": f"https://example.test/{app_env}/oauth/hh/callback",
                "HH_USER_AGENT": (
                    f"AI-Career-Agent-{app_env}/1.0 (tests@example.invalid)"
                ),
            }
        )

    return environment


def _import_application(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    script = """
import json
import app
print(json.dumps({
    "environment": app.SETTINGS.environment,
    "testing": bool(app.app.config["TESTING"]),
    "debug": bool(app.app.config["DEBUG"]),
    "sync_enabled": bool(app.TRUDVSEM_SYNC_ENABLED),
}))
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize(
    ("app_env", "expected_testing", "expected_debug"),
    [
        ("production", False, False),
        ("development", False, True),
        ("test", True, False),
    ],
)
def test_application_imports_in_each_supported_mode(
    tmp_path,
    app_env,
    expected_testing,
    expected_debug,
):
    result = _import_application(_base_environment(tmp_path, app_env))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload == {
        "environment": app_env,
        "testing": expected_testing,
        "debug": expected_debug,
        "sync_enabled": False,
    }


def test_production_import_fails_early_with_clear_missing_variable_names(tmp_path):
    environment = _base_environment(tmp_path, "production")
    for name in REQUIRED_NAMES:
        environment.pop(name, None)

    result = _import_application(environment)

    assert result.returncode != 0
    assert "ConfigurationError" in result.stderr
    assert "FLASK_SECRET_KEY" in result.stderr
    assert "TOKEN_ENCRYPTION_KEY" in result.stderr
    assert "HH_USER_AGENT" in result.stderr

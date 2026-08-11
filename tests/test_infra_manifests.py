from __future__ import annotations

from pathlib import Path

import yaml

from scripts import infra_manifest_check

ROOT = Path(__file__).resolve().parents[1]


def test_infra_manifest_check_passes_current_repository():
    assert infra_manifest_check.validate(ROOT) == []


def test_compose_has_isolated_postgresql_and_profiles():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert services["db"]["image"].startswith("postgres:17")
    assert "ports" not in services["db"]
    assert compose["networks"]["backend"]["internal"] is True
    assert services["restore-db"]["profiles"] == ["restore-test"]
    assert services["ops"]["profiles"] == ["ops"]
    assert services["gateway"]["profiles"] == ["tls"]
    assert services["sync-worker"]["profiles"] == ["sync"]
    assert services["sync-worker"]["command"] == [
        "python",
        "scripts/trudvsem_sync_worker.py",
    ]
    assert "ports" not in services["sync-worker"]
    app_environment = compose["x-app-environment"]
    assert app_environment["AUTH_EMAIL_BACKEND"] == "${AUTH_EMAIL_BACKEND:-disabled}"
    assert app_environment["AUTH_SESSION_TTL_SECONDS"] == "${AUTH_SESSION_TTL_SECONDS:-43200}"
    assert app_environment["SEARCH_PAGE_SIZE"] == "${SEARCH_PAGE_SIZE:-20}"
    assert app_environment["AUTH_SMTP_USE_TLS"] == "${AUTH_SMTP_USE_TLS:-1}"
    assert app_environment["AUTH_SMTP_USE_SSL"] == "${AUTH_SMTP_USE_SSL:-0}"
    assert app_environment["AUTH_GMAIL_CLIENT_ID"] == "${AUTH_GMAIL_CLIENT_ID:-}"
    assert app_environment["AUTH_GMAIL_CLIENT_SECRET"] == "${AUTH_GMAIL_CLIENT_SECRET:-}"
    assert app_environment["AUTH_GMAIL_REFRESH_TOKEN"] == "${AUTH_GMAIL_REFRESH_TOKEN:-}"
    assert app_environment["AUTH_GMAIL_TIMEOUT_SECONDS"] == "${AUTH_GMAIL_TIMEOUT_SECONDS:-8}"
    assert app_environment["SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST"] == "${SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST:-1}"


def test_dockerfile_has_non_root_runtime_and_ops_targets():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "AS runtime" in text
    assert "AS ops" in text
    assert text.count("USER app") >= 2
    assert "postgres:17-bookworm" in text
    assert "HEALTHCHECK" in text


def test_env_template_contains_placeholders_not_real_secrets():
    text = (ROOT / "infra/vps/.env.example").read_text(encoding="utf-8")
    assert "CHANGE_ME_STRONG_DATABASE_PASSWORD" in text
    assert "AUTH_EMAIL_BACKEND=smtp" in text
    assert "AUTH_SMTP_PASSWORD=CHANGE_ME_SMTP_PASSWORD" in text
    assert "AUTH_SMTP_USE_TLS=1" in text
    assert "AUTH_SMTP_USE_SSL=0" in text
    assert "AUTH_GMAIL_CLIENT_ID=CHANGE_ME_GMAIL_OAUTH_CLIENT_ID" in text
    assert "AUTH_GMAIL_CLIENT_SECRET=CHANGE_ME_GMAIL_OAUTH_CLIENT_SECRET" in text
    assert "AUTH_GMAIL_REFRESH_TOKEN=CHANGE_ME_GMAIL_REFRESH_TOKEN" in text
    assert "AUTH_GMAIL_TIMEOUT_SECONDS=8" in text
    assert "AUTH_SESSION_TTL_SECONDS=43200" in text
    assert "AUTH_VERIFICATION_TTL_SECONDS=86400" in text
    assert "AUTH_RESET_TTL_SECONDS=3600" in text
    assert "AUTH_PASSWORD_MIN_LENGTH=12" in text
    assert "SEARCH_PAGE_SIZE=20" in text
    assert "SEARCH_SNAPSHOT_TTL_SECONDS=1800" in text
    assert "SEARCH_SNAPSHOT_MAX_CANDIDATES=1200" in text
    assert "SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE=8" in text
    assert "SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1" in text
    assert "SEARCH_SNAPSHOT_BUFFER_ITEMS=1" in text
    assert "SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS=90" in text
    assert "TRUDVSEM_SYNC_ENABLED=0" in text
    assert "TRUDVSEM_SYNC_INTERVAL=1800" in text
    assert "TRUDVSEM_SYNC_ITEMS=300" in text
    assert "TRUDVSEM_SYNC_BATCH=10" in text
    assert "TRUDVSEM_SYNC_POLL_SECONDS=15" in text
    assert "TRUDVSEM_SYNC_STALE_SECONDS=900" in text
    assert "TRUDVSEM_WORKER_HEARTBEAT_SECONDS=15" in text
    assert "TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS=300" in text
    assert "TRUDVSEM_VACANCY_TTL_DAYS=45" in text
    assert "TRUDVSEM_CLOSED_RETENTION_DAYS=30" in text
    assert "TRUDVSEM_RETRY_BASE_SECONDS=60" in text
    assert "TRUDVSEM_RETRY_MAX_SECONDS=3600" in text
    assert "GUNICORN_WORKERS=1" in text
    assert "postgresql+psycopg://restore_user:CHANGE_ME" in text


def test_render_uses_external_worker_runtime_supervisor():
    render = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))
    service = render["services"][0]
    assert "scripts/start_runtime.py" in service["startCommand"]
    env = {item["key"]: item for item in service["envVars"]}
    assert env["AUTH_EMAIL_BACKEND"]["value"] == "disabled"
    assert env["AUTH_SMTP_PASSWORD"]["sync"] is False
    assert env["AUTH_SMTP_USE_TLS"]["value"] == "1"
    assert env["AUTH_SMTP_USE_SSL"]["value"] == "0"
    assert env["AUTH_GMAIL_CLIENT_ID"]["sync"] is False
    assert env["AUTH_GMAIL_CLIENT_SECRET"]["sync"] is False
    assert env["AUTH_GMAIL_REFRESH_TOKEN"]["sync"] is False
    assert env["AUTH_GMAIL_TIMEOUT_SECONDS"]["value"] == "8"
    assert env["SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST"]["value"] == "1"

    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "TRUDVSEM_SYNC_THREAD" not in app_text
    assert "TRUDVSEM_SYNC_EVENT" not in app_text

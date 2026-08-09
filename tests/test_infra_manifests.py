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

    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "TRUDVSEM_SYNC_THREAD" not in app_text
    assert "TRUDVSEM_SYNC_EVENT" not in app_text

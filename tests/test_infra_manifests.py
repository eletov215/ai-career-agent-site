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
    assert "TRUDVSEM_SYNC_ENABLED=0" in text
    assert "GUNICORN_WORKERS=1" in text
    assert "postgresql+psycopg://restore_user:CHANGE_ME" in text

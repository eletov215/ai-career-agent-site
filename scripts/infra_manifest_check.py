#!/usr/bin/env python3
"""Validate INFRA-001 Docker/Compose security and portability invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_yaml(path: str) -> dict[str, Any]:
    data = yaml.safe_load(_read(path))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def validate(root: Path = ROOT) -> list[str]:
    global ROOT
    previous = ROOT
    ROOT = root.resolve()
    errors: list[str] = []
    try:
        required_files = [
            "Dockerfile",
            ".dockerignore",
            "compose.yaml",
            "infra/gunicorn.conf.py",
            "infra/vps/.env.example",
            "infra/vps/compose.test.env",
            "infra/vps/Caddyfile",
            "scripts/infra_probe.py",
            "scripts/infra_container_smoke.sh",
            "scripts/start_runtime.py",
            "scripts/sync_trudvsem.py",
            "scripts/trudvsem_sync_worker.py",
        ]
        for relative in required_files:
            if not (ROOT / relative).is_file():
                errors.append(f"missing required file: {relative}")

        if errors:
            return errors

        dockerfile = _read("Dockerfile")
        for marker in ["AS runtime", "AS ops", "USER app", "HEALTHCHECK", "postgres:17-bookworm"]:
            if marker not in dockerfile:
                errors.append(f"Dockerfile missing invariant: {marker}")
        if re.search(r"(?im)^\s*(ENV|ARG)\s+.*(SECRET|PASSWORD|TOKEN)=\S+", dockerfile):
            errors.append("Dockerfile must not bake secret values")

        compose = _load_yaml("compose.yaml")
        services = compose.get("services")
        if not isinstance(services, dict):
            errors.append("compose.yaml services mapping is missing")
            return errors
        required_services = {
            "db",
            "restore-db",
            "migrate",
            "web",
            "sync-worker",
            "gateway",
            "ops",
        }
        missing_services = sorted(required_services - set(services))
        if missing_services:
            errors.append(f"compose.yaml missing services: {', '.join(missing_services)}")

        db = services.get("db", {})
        if db.get("ports"):
            errors.append("db service must not publish a host port")
        if "postgres:17" not in str(db.get("image", "")):
            errors.append("db service must use PostgreSQL 17")
        if "backend" not in (db.get("networks") or []):
            errors.append("db service must use the backend network")

        networks = compose.get("networks") or {}
        backend = networks.get("backend") if isinstance(networks, dict) else None
        if not isinstance(backend, dict) or backend.get("internal") is not True:
            errors.append("backend network must be internal: true")

        restore = services.get("restore-db", {})
        if "restore-test" not in (restore.get("profiles") or []):
            errors.append("restore-db must be behind the restore-test profile")
        if restore.get("ports"):
            errors.append("restore-db must not publish a host port")

        migrate = services.get("migrate", {})
        if migrate.get("restart") != "no":
            errors.append("migrate service must be one-shot with restart: no")
        command = migrate.get("command") or []
        if "scripts/manage_db.py" not in " ".join(map(str, command)):
            errors.append("migrate service must run scripts/manage_db.py upgrade")

        web = services.get("web", {})
        web_health = web.get("healthcheck") or {}
        if "/health/ready" not in json.dumps(web_health):
            errors.append("web healthcheck must use /health/ready")
        web_env = web.get("environment") or {}
        if isinstance(web_env, dict) and str(web_env.get("TRUDVSEM_SYNC_ENABLED", "0")) not in {"0", "${TRUDVSEM_SYNC_ENABLED:-0}"}:
            errors.append("test VPS must not enable embedded Trudvsem sync by default")

        sync_worker = services.get("sync-worker", {})
        if "sync" not in (sync_worker.get("profiles") or []):
            errors.append("sync-worker must be behind the sync profile")
        worker_command = " ".join(map(str, sync_worker.get("command") or []))
        if "scripts/trudvsem_sync_worker.py" not in worker_command:
            errors.append("sync-worker must run scripts/trudvsem_sync_worker.py")
        worker_env = sync_worker.get("environment") or {}
        if not isinstance(worker_env, dict) or str(
            worker_env.get("TRUDVSEM_SYNC_ENABLED", "")
        ) != "1":
            errors.append("sync-worker must explicitly enable Trudvsem sync")
        if sync_worker.get("ports"):
            errors.append("sync-worker must not publish a host port")

        gateway = services.get("gateway", {})
        if "tls" not in (gateway.get("profiles") or []):
            errors.append("gateway must be behind the tls profile")
        if "./infra/vps/Caddyfile:/etc/caddy/Caddyfile:ro" not in (gateway.get("volumes") or []):
            errors.append("gateway must mount the repository Caddyfile read-only")

        ops = services.get("ops", {})
        if "ops" not in (ops.get("profiles") or []):
            errors.append("ops service must be behind the ops profile")
        ops_build = ops.get("build") or {}
        if not isinstance(ops_build, dict) or ops_build.get("target") != "ops":
            errors.append("ops service must build the Dockerfile ops target")

        dockerignore = _read(".dockerignore")
        for marker in [".env", "__pycache__/", "*.db", "*.dump", "backups/"]:
            if marker not in dockerignore:
                errors.append(f".dockerignore missing: {marker}")

        env_example = _read("infra/vps/.env.example")
        for marker in [
            "CHANGE_ME",
            "SEARCH_SNAPSHOT_TTL_SECONDS=1800",
            "SEARCH_SNAPSHOT_MAX_CANDIDATES=1200",
            "SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE=8",
            "SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=3",
            "SEARCH_SNAPSHOT_BUFFER_ITEMS=1",
            "SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS=90",
            "TRUDVSEM_SYNC_ENABLED=0",
            "TRUDVSEM_SYNC_INTERVAL=1800",
            "TRUDVSEM_SYNC_ITEMS=300",
            "TRUDVSEM_SYNC_BATCH=10",
            "TRUDVSEM_SYNC_POLL_SECONDS=15",
            "TRUDVSEM_SYNC_STALE_SECONDS=900",
            "TRUDVSEM_WORKER_HEARTBEAT_SECONDS=15",
            "TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS=300",
            "TRUDVSEM_VACANCY_TTL_DAYS=45",
            "TRUDVSEM_CLOSED_RETENTION_DAYS=30",
            "TRUDVSEM_RETRY_BASE_SECONDS=60",
            "TRUDVSEM_RETRY_MAX_SECONDS=3600",
            "GUNICORN_WORKERS=1",
            "BACKUP_ENCRYPTION_KEY",
        ]:
            if marker not in env_example:
                errors.append(f"VPS env template missing: {marker}")
        if re.search(r"(?i)(password|secret|token|key)=((?!CHANGE_ME)[^\s#]+)", env_example):
            # Allow explicit empty REED_API_KEY only.
            suspect = [
                line for line in env_example.splitlines()
                if re.search(r"(?i)(password|secret|token|key)=", line)
                and "CHANGE_ME" not in line
                and not line.endswith("=")
            ]
            if suspect:
                errors.append("VPS env template contains a non-placeholder credential")

        test_env = _read("infra/vps/compose.test.env")
        if "APP_ENV=test" not in test_env or "WEB_PUBLISH_PORT=18000" not in test_env:
            errors.append("compose.test.env must be an isolated test environment")

        caddyfile = _read("infra/vps/Caddyfile")
        if "reverse_proxy web:8000" not in caddyfile or "admin off" not in caddyfile:
            errors.append("Caddyfile must disable admin API and proxy only to web:8000")

        render = _load_yaml("render.yaml")
        render_services = render.get("services") or []
        render_start = ""
        if render_services and isinstance(render_services[0], dict):
            render_start = str(render_services[0].get("startCommand") or "")
        if "scripts/start_runtime.py" not in render_start:
            errors.append("Render web service must start the SYNC-001 runtime supervisor")

        app_text = _read("app.py")
        forbidden_web_worker_markers = (
            "TRUDVSEM_SYNC_THREAD",
            "TRUDVSEM_SYNC_EVENT",
            "threading.Thread(",
        )
        for marker in forbidden_web_worker_markers:
            if marker in app_text:
                errors.append(f"app.py must not own Trudvsem worker lifecycle: {marker}")

        return errors
    finally:
        ROOT = previous


def main() -> int:
    errors = validate(ROOT)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

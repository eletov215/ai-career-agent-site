#!/usr/bin/env python3
"""Periodic identifier-safe retention cleanup worker for PRIV-001."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings  # noqa: E402
from database import create_database  # noqa: E402
from observability import configure_logging  # noqa: E402
from repositories.privacy import PrivacyRepository  # noqa: E402
from services.privacy import PrivacyService  # noqa: E402

_STOP = False
_ADVISORY_LOCK_KEY = 202608130013


def _stop(_signum=None, _frame=None) -> None:  # noqa: ANN001
    global _STOP
    _STOP = True


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def _cleanup_lock(database, settings):  # noqa: ANN001
    if database.backend == "postgresql":
        connection = database.engine.connect()
        try:
            acquired = bool(
                connection.scalar(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": _ADVISORY_LOCK_KEY},
                )
            )
            yield acquired
        finally:
            try:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _ADVISORY_LOCK_KEY},
                )
            except Exception:
                pass
            connection.close()
        return

    lock_path = settings.data_dir / "privacy_cleanup.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    acquired = False
    try:
        for _attempt in range(2):
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, "w", encoding="ascii") as handle:
                    handle.write(str(os.getpid()))
                acquired = True
                break
            except FileExistsError:
                try:
                    raw = lock_path.read_text(encoding="ascii").strip()
                    owner_pid = int(raw)
                except (OSError, ValueError):
                    owner_pid = -1
                if _pid_alive(owner_pid):
                    break
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
        yield acquired
    finally:
        if acquired:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def _write_heartbeat(settings, *, status: str, counts=None, error: str | None = None) -> None:  # noqa: ANN001
    path = settings.data_dir / "privacy_cleanup_heartbeat.json"
    payload = {
        "pid": os.getpid(),
        "timestamp": int(time.time()),
        "status": status,
        "counts": {str(k): int(v) for k, v in (counts or {}).items()},
    }
    if error:
        payload["error_type"] = error[:80]
    # The PostgreSQL advisory-lock path does not create DATA_DIR. This worker
    # must be independent of Gunicorn/other workers winning the startup race.
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True)
    tmp = None
    try:
        # Lock-busy workers also publish heartbeats. Give each writer its own
        # private file on the same filesystem, then replace the complete JSON.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix="privacy_cleanup_heartbeat.", suffix=".tmp", delete=False,
        ) as handle:
            tmp = Path(handle.name)
            handle.write(serialized)
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass


def _publish_heartbeat(settings, logger, **payload) -> None:  # noqa: ANN001
    """Report diagnostic I/O failures without relabelling or rerunning cleanup."""
    try:
        _write_heartbeat(settings, **payload)
    except OSError as exc:
        # Do not attempt an error-heartbeat on the same failing filesystem.
        # Preserve the last good file; its timestamp remains stale until recovery.
        # Log the exception class only, never a path, payload or raw exception.
        logger.error(
            "Privacy cleanup heartbeat write failed",
            extra={"event": "privacy_retention_heartbeat_failed", "error_type": type(exc).__name__},
        )


def main() -> int:
    settings = load_settings()
    configure_logging(settings)
    logger = logging.getLogger("privacy_cleanup_worker")
    database = create_database(settings.database_url)
    service = PrivacyService(PrivacyRepository(database), settings)
    for signal_name in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_name, _stop)
    try:
        while not _STOP:
            heartbeat_status = "error"
            counts = {}
            error_type = None
            try:
                with _cleanup_lock(database, settings) as acquired:
                    if not acquired:
                        logger.info(
                            "Privacy retention cleanup skipped because another worker owns the lock",
                            extra={"event": "privacy_retention_cleanup_lock_busy"},
                        )
                        heartbeat_status = "lock_busy"
                    else:
                        counts = service.run_retention_cleanup()
                        logger.info(
                            "Privacy retention cleanup completed",
                            extra={
                                "event": "privacy_retention_cleanup",
                                "pending_account_count": counts.get("pending_accounts", 0),
                                "auth_session_count": counts.get("auth_sessions", 0),
                                "auth_token_count": counts.get("auth_tokens", 0),
                                "audit_event_count": counts.get("audit_events", 0),
                                "orphan_resume_asset_count": counts.get("orphan_resume_assets", 0),
                                "legacy_oauth_mirror_count": counts.get("legacy_oauth_mirrors", 0),
                            },
                        )
                        heartbeat_status = "ok"
            except Exception as exc:
                logger.exception(
                    "Privacy retention cleanup failed",
                    extra={"event": "privacy_retention_cleanup_failed"},
                )
                error_type = type(exc).__name__
            _publish_heartbeat(
                settings, logger, status=heartbeat_status, counts=counts, error=error_type,
            )
            deadline = time.monotonic() + settings.privacy_cleanup_interval_seconds
            while not _STOP and time.monotonic() < deadline:
                time.sleep(min(5, max(0.1, deadline - time.monotonic())))
        return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

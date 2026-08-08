#!/usr/bin/env python3
"""Long-running external worker for durable Trudvsem synchronization jobs."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_settings
from database import create_database
from observability import configure_logging, provider_operation
from services.storage import StorageServices
from services.trudvsem_sync import TrudvsemSyncService

logger = logging.getLogger("trudvsem_sync_worker")
_STOP_REQUESTED = False


def _request_stop(signum, _frame) -> None:  # noqa: ANN001
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    logger.info(
        "Trudvsem worker stop requested",
        extra={"event": "trudvsem_worker_stop_requested", "signal": signum},
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Poll durable Trudvsem sync jobs outside the web process.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queued/due run and exit.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = load_settings()
    configure_logging(settings)

    if not settings.trudvsem_sync_enabled:
        logger.info(
            "Trudvsem external worker disabled",
            extra={"event": "trudvsem_worker_disabled"},
        )
        return 0

    for signal_name in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_name, _request_stop)

    database = create_database(settings.database_url)
    storage = StorageServices.from_database(database)
    service = TrudvsemSyncService(
        settings=settings,
        database=database,
        vacancy_store=storage.vacancies,
        sync_runs=storage.sync_runs,
        sync_checkpoints=storage.sync_checkpoints,
        provider_operation_factory=provider_operation,
    )
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
    heartbeat_interval = settings.trudvsem_worker_heartbeat_seconds
    poll_interval = settings.trudvsem_sync_poll_seconds
    next_heartbeat = 0.0

    def heartbeat(current_run_id: str | None, *, status: str = "running") -> None:
        nonlocal next_heartbeat
        now = time.monotonic()
        if current_run_id is not None or now >= next_heartbeat:
            storage.sync_workers.heartbeat(
                worker_id=worker_id,
                source="trudvsem",
                status=status,
                current_run_id=current_run_id,
                details={
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "mode": "external_process",
                },
            )
            next_heartbeat = now + heartbeat_interval

    logger.info(
        "Trudvsem external worker started",
        extra={
            "event": "trudvsem_worker_started",
            "worker_id": worker_id,
            "poll_seconds": poll_interval,
        },
    )

    exit_code = 0
    try:
        storage.sync_workers.prune_stale(
            stale_before=int(time.time()) - max(heartbeat_interval * 6, 600)
        )
        while not _STOP_REQUESTED:
            heartbeat(None, status="idle")
            active = service.active_run()
            should_run = service.should_run(active)
            if should_run:
                heartbeat(active.id if active else None, status="running")
                result = service.run_once(
                    trigger="scheduled-worker",
                    queued_run_id=(
                        active.id if active and active.status == "queued" else None
                    ),
                    heartbeat=lambda run_id: heartbeat(
                        run_id,
                        status="running" if run_id else "idle",
                    ),
                )
                if args.once and result.status == "failed":
                    exit_code = 1
                heartbeat(None, status="idle")

            if args.once:
                break

            deadline = time.monotonic() + poll_interval
            while not _STOP_REQUESTED and time.monotonic() < deadline:
                heartbeat(None, status="idle")
                time.sleep(min(1.0, max(0.1, deadline - time.monotonic())))
    finally:
        try:
            storage.sync_workers.remove(worker_id)
        except Exception:
            logger.exception("Could not remove Trudvsem worker heartbeat")
        database.dispose()
        logger.info(
            "Trudvsem external worker stopped",
            extra={"event": "trudvsem_worker_stopped", "worker_id": worker_id},
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

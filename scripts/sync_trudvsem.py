#!/usr/bin/env python3
"""Run or enqueue one Trudvsem synchronization job outside Gunicorn."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_settings
from database import create_database
from observability import configure_logging, provider_operation
from services.storage import StorageServices
from services.trudvsem_sync import TrudvsemSyncService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one external Trudvsem cache synchronization.",
    )
    parser.add_argument("--trigger", default="manual-cli")
    parser.add_argument("--target", type=int)
    parser.add_argument("--queued-run-id")
    parser.add_argument(
        "--enqueue-only",
        action="store_true",
        help="Create an idempotent queued job and exit without provider I/O.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = load_settings()
    configure_logging(settings)
    database = create_database(settings.database_url)
    storage = StorageServices.from_database(database)
    service = TrudvsemSyncService(
        settings=settings,
        database=database,
        vacancy_store=storage.vacancies,
        sync_runs=storage.sync_runs,
        provider_operation_factory=provider_operation,
    )
    try:
        if args.enqueue_only:
            run = service.enqueue(
                trigger=args.trigger,
                target=args.target,
                details={"requested_by": "cli"},
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "status": run.status,
                        "source": run.source,
                        "run_id": run.id,
                        "trigger": run.trigger,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        result = service.run_once(
            trigger=args.trigger,
            queued_run_id=args.queued_run_id,
            target=args.target,
        )
        print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.ok else 1
    finally:
        database.dispose()


if __name__ == "__main__":
    sys.exit(main())

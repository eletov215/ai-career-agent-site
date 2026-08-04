#!/usr/bin/env python3
"""Run database migrations and secret-free readiness checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_database_url  # noqa: E402
from database import (  # noqa: E402
    create_database,
    current_revision,
    database_health,
    upgrade_database,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("upgrade", "current", "check"),
        help="Database maintenance command.",
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="Target Alembic revision for upgrade (default: head).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url, explicit = load_database_url()

    if args.command == "upgrade":
        upgrade_database(database_url, args.revision)

    runtime = create_database(database_url)
    try:
        health = database_health(runtime)
        revision = current_revision(runtime.engine)
        if args.command == "current":
            print(revision or "unversioned")
            return 0
        if not health["ok"]:
            print("Database readiness check failed.", file=sys.stderr)
            return 1
        if revision is None:
            print("Database schema is not managed by Alembic.", file=sys.stderr)
            return 1
        print(
            "Database ready: "
            f"backend={runtime.backend}, persistent={runtime.persistent}, "
            f"configured={explicit}, revision={revision}"
        )
        return 0
    finally:
        runtime.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

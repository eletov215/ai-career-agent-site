#!/usr/bin/env python3
"""Restore a validated backup into RESTORE_DATABASE_URL and verify counts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.backup import BackupError, restore_database  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required for an intentional production restore.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_url = os.getenv("RESTORE_DATABASE_URL", "").strip()
    if not target_url:
        print(
            json.dumps(
                {"ok": False, "error": "RESTORE_DATABASE_URL is required"},
                ensure_ascii=False,
            )
        )
        return 1
    try:
        result = restore_database(
            args.backup,
            target_url,
            manifest_path=args.manifest,
            encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY"),
            environment=os.getenv("APP_ENV", "production"),
            allow_production=args.allow_production,
            clean=args.clean,
        )
    except BackupError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "verified": result.verified,
                "backend": result.target_backend,
                "database_revision": result.database_revision,
                "table_counts": result.table_counts,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

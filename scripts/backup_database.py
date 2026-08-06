#!/usr/bin/env python3
"""Create an encrypted, checksummed database backup and manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_database_url  # noqa: E402
from operations.backup import BackupError, backup_database, prune_backups  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=os.getenv("BACKUP_DIR", "backups"))
    parser.add_argument("--name", help="Deterministic backup filename for automation/tests.")
    parser.add_argument(
        "--allow-unencrypted",
        action="store_true",
        help="Explicitly allow an unencrypted backup (blocked by default in production).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.getenv("BACKUP_RETENTION_DAYS", "14")),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    database_url, _explicit = load_database_url()
    try:
        result = backup_database(
            database_url,
            args.output_dir,
            output_name=args.name,
            encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY"),
            environment=os.getenv("APP_ENV", "production"),
            allow_unencrypted=args.allow_unencrypted,
            service_name=os.getenv("SERVICE_NAME", "ai-career-agent"),
            app_version=os.getenv("APP_VERSION")
            or os.getenv("RENDER_GIT_COMMIT", "unknown")[:80],
        )
        removed = prune_backups(
            args.output_dir,
            retention_days=args.retention_days,
        )
    except BackupError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "backup_path": str(result.backup_path),
                "manifest_path": str(result.manifest_path),
                "encrypted": result.manifest["encrypted"],
                "size_bytes": result.manifest["size_bytes"],
                "sha256": result.manifest["sha256"],
                "database_revision": result.manifest["database_revision"],
                "table_counts": result.manifest["table_counts"],
                "pruned_files": len(removed),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify a backup manifest, size, and SHA-256 without restoring data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.backup import BackupError, validate_backup  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--manifest")
    args = parser.parse_args()
    try:
        manifest = validate_backup(args.backup, args.manifest)
    except BackupError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "encrypted": manifest.get("encrypted"),
                "size_bytes": manifest.get("size_bytes"),
                "sha256": manifest.get("sha256"),
                "database_revision": manifest.get("database_revision"),
                "table_counts": manifest.get("table_counts"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

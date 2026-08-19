#!/usr/bin/env python3
"""Run one PRIV-001 retention cleanup iteration."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings  # noqa: E402
from database import create_database  # noqa: E402
from repositories.privacy import PrivacyRepository  # noqa: E402
from services.privacy import PrivacyService  # noqa: E402


def main() -> int:
    settings = load_settings()
    database = create_database(settings.database_url)
    try:
        service = PrivacyService(PrivacyRepository(database), settings)
        counts = service.run_retention_cleanup()
        print(
            "privacy cleanup completed: "
            + ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        )
        return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

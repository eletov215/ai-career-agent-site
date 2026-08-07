"""Cross-process synchronization lock for provider workers."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from sqlalchemy import text

from database import DatabaseRuntime


def _lock_key(source: str) -> int:
    digest = hashlib.sha256(f"ai-career-agent:sync:{source}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


class SyncExecutionLock:
    """Hold a PostgreSQL advisory lock or a SQLite-compatible lock file."""

    def __init__(
        self,
        database: DatabaseRuntime,
        *,
        source: str,
        data_dir: Path,
        stale_seconds: int,
    ) -> None:
        self.database = database
        self.source = source
        self.data_dir = Path(data_dir)
        self.stale_seconds = max(60, int(stale_seconds))
        self.acquired = False
        self._connection = None
        self._lock_path = self.data_dir / "locks" / f"sync-{source}.lock"

    def __enter__(self) -> "SyncExecutionLock":
        if self.database.backend == "postgresql":
            connection = self.database.engine.connect()
            acquired = bool(
                connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_key)"),
                    {"lock_key": _lock_key(self.source)},
                )
            )
            if not acquired:
                connection.close()
                return self
            self._connection = connection
            self.acquired = True
            return self

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        for _attempt in range(2):
            try:
                descriptor = os.open(
                    self._lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    age = time.time() - self._lock_path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age <= self.stale_seconds:
                    return self
                try:
                    self._lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            else:
                payload = {
                    "pid": os.getpid(),
                    "created_at": int(time.time()),
                    "source": self.source,
                }
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, sort_keys=True)
                self.acquired = True
                return self
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        if self._connection is not None:
            try:
                self._connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": _lock_key(self.source)},
                )
            finally:
                self._connection.close()
                self._connection = None
        elif self.acquired:
            try:
                self._lock_path.unlink()
            except FileNotFoundError:
                pass
        self.acquired = False

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from config import load_database_url
from database import CURRENT_REVISION, create_database, upgrade_database
from operations.backup import (
    BackupError,
    _postgres_environment,
    backup_database,
    prune_backups,
    restore_database,
    validate_backup,
)
from services.storage import StorageServices


BACKUP_KEY = base64.urlsafe_b64encode(b"K" * 32).decode("ascii")


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _seed_database(database_url: str) -> None:
    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        storage = StorageServices.from_database(runtime)
        storage.users.create(
            email="backup@example.test",
            display_name="Backup Test",
            status="active",
            user_id="backup-user",
        )
        run = storage.sync_runs.start(
            source="trudvsem",
            trigger="backup-test",
            target=5,
        )
        storage.sync_runs.finish(
            run.id,
            status="succeeded",
            processed=5,
            saved=4,
            cursor="5",
        )
    finally:
        runtime.dispose()




def test_maintenance_scripts_can_import_project_modules_from_cli():
    project_root = Path(__file__).resolve().parents[1]
    for script_name in (
        "backup_database.py",
        "restore_database.py",
        "verify_backup.py",
    ):
        process = subprocess.run(
            [sys.executable, str(project_root / "scripts" / script_name), "--help"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert process.returncode == 0, process.stderr

def test_encrypted_sqlite_backup_restore_round_trip(tmp_path):
    source_url = sqlite_url(tmp_path / "source.db")
    target_url = sqlite_url(tmp_path / "restored.db")
    _seed_database(source_url)

    result = backup_database(
        source_url,
        tmp_path / "backups",
        output_name="ops-test.sqlite3",
        encryption_key=BACKUP_KEY,
        environment="test",
        service_name="career-test",
        app_version="test-version",
    )

    assert result.backup_path.name.endswith(".sqlite3.enc")
    assert result.manifest["encrypted"] is True
    assert result.manifest["database_revision"] == CURRENT_REVISION
    assert result.manifest["table_counts"]["users"] == 1
    assert result.manifest["table_counts"]["sync_runs"] == 1
    assert validate_backup(result.backup_path) == result.manifest

    restored = restore_database(
        result.backup_path,
        target_url,
        encryption_key=BACKUP_KEY,
        environment="test",
    )

    assert restored.verified is True
    assert restored.database_revision == CURRENT_REVISION
    assert restored.table_counts["users"] == 1
    assert restored.table_counts["sync_runs"] == 1

    runtime = create_database(target_url)
    try:
        storage = StorageServices.from_database(runtime)
        assert storage.users.get("backup-user").email == "backup@example.test"
        assert storage.sync_runs.latest("trudvsem").saved == 4
    finally:
        runtime.dispose()


def test_backup_validation_rejects_tampering(tmp_path):
    source_url = sqlite_url(tmp_path / "source.db")
    _seed_database(source_url)
    result = backup_database(
        source_url,
        tmp_path / "backups",
        output_name="tamper.sqlite3",
        encryption_key=BACKUP_KEY,
        environment="test",
    )

    with result.backup_path.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(BackupError, match="Размер|сумма"):
        validate_backup(result.backup_path)


def test_production_backup_requires_explicit_encryption(tmp_path):
    source_url = sqlite_url(tmp_path / "source.db")
    _seed_database(source_url)

    with pytest.raises(BackupError, match="Production backup требует"):
        backup_database(
            source_url,
            tmp_path / "backups",
            output_name="plain.sqlite3",
            environment="production",
        )


def test_production_restore_requires_explicit_override(tmp_path):
    source_url = sqlite_url(tmp_path / "source.db")
    _seed_database(source_url)
    result = backup_database(
        source_url,
        tmp_path / "backups",
        output_name="restore-guard.sqlite3",
        encryption_key=BACKUP_KEY,
        environment="test",
    )

    with pytest.raises(BackupError, match="production заблокирован"):
        restore_database(
            result.backup_path,
            sqlite_url(tmp_path / "target.db"),
            encryption_key=BACKUP_KEY,
            environment="production",
        )


def test_postgres_connection_password_is_only_in_process_environment():
    url = make_url(
        "postgresql+psycopg://career:very-secret@db.example.test:5432/career?sslmode=require"
    )
    environment = _postgres_environment(url)

    assert environment["PGPASSWORD"] == "very-secret"
    assert environment["PGHOST"] == "db.example.test"
    assert environment["PGDATABASE"] == "career"
    assert environment["PGSSLMODE"] == "require"
    safe_identity = {
        "host": url.host,
        "database": url.database,
        "port": url.port,
    }
    assert "very-secret" not in json.dumps(safe_identity)


def test_prune_backups_removes_only_expired_backup_artifacts(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old_backup = backup_dir / "old.dump.enc"
    old_manifest = backup_dir / "old.dump.enc.manifest.json"
    keep = backup_dir / "keep.dump.enc"
    unrelated = backup_dir / "notes.txt"
    for path in (old_backup, old_manifest, keep, unrelated):
        path.write_text("x")
    old_time = 1_700_000_000
    for path in (old_backup, old_manifest):
        path.touch()
        import os

        os.utime(path, (old_time, old_time))

    removed = prune_backups(
        backup_dir,
        retention_days=7,
        now_timestamp=old_time + 8 * 86_400,
    )

    assert old_backup in removed
    assert old_manifest in removed
    assert keep.exists()
    assert unrelated.exists()

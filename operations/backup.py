"""Encrypted database backup and verified restore helpers for OPS-001.

PostgreSQL uses the standard ``pg_dump`` custom format and ``pg_restore``.
SQLite uses the sqlite3 online-backup API for local/test environments.  Backup
contents can be encrypted with an independent 32-byte URL-safe base64 key using
AES-256-GCM.  Manifests contain only secret-free database identity, schema
revision, table counts, size, and SHA-256.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from sqlalchemy import inspect, text
from sqlalchemy.engine import URL, make_url

from database import create_database, current_revision


_BACKUP_FORMAT_VERSION = 1
_ENCRYPTION_MAGIC = b"ACAOPS1"
_NONCE_SIZE = 12
_TAG_SIZE = 16
_INVENTORY_TABLES = (
    "users",
    "oauth_connections",
    "auth_sessions",
    "auth_tokens",
    "career_profiles",
    "career_profile_versions",
    "resume_drafts",
    "resume_versions",
    "resume_assets",
    "resume_exports",
    "privacy_audit_events",
    "source_health_states",
    "resume_interview_sessions", "resume_interview_events",
    "vacancy_match_series", "vacancy_match_reports",
    "resume_analysis_reports", "resume_analysis_decisions", "resume_analysis_review_events",
    "ai_runtime_policies", "ai_usage_events", "ai_budget_buckets", "ai_request_leases",
    "ai_provider_states", "ai_plan_entitlements", "ai_user_plans",
    "vacancies",
    "vacancy_source_records",
    "sync_runs",
    "sync_checkpoints",
    "search_snapshots",
    "search_snapshot_sources",
    "search_snapshot_candidates",
    "search_snapshot_items",
    "accounts",
    "hh_accounts",
)


class BackupError(RuntimeError):
    """Raised when a backup cannot be created, validated, or restored safely."""


@dataclass(frozen=True, slots=True)
class BackupResult:
    backup_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RestoreResult:
    target_backend: str
    database_revision: str | None
    table_counts: dict[str, int]
    verified: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _secure_permissions(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        # Best effort on platforms that do not support POSIX permissions.
        pass


def _decode_encryption_key(value: str | bytes | None) -> bytes | None:
    if value is None or value == "":
        return None
    raw = value.encode("ascii") if isinstance(value, str) else value
    try:
        key = base64.urlsafe_b64decode(raw)
    except (ValueError, TypeError, base64.binascii.Error) as exc:
        raise BackupError(
            "BACKUP_ENCRYPTION_KEY должен быть URL-safe base64 ключом из 32 байт."
        ) from exc
    if len(key) != 32:
        raise BackupError(
            "BACKUP_ENCRYPTION_KEY после декодирования должен содержать 32 байта."
        )
    return key


def _encrypt_file(source: Path, target: Path, key: bytes) -> None:
    nonce = os.urandom(_NONCE_SIZE)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    with source.open("rb") as input_handle, target.open("wb") as output_handle:
        output_handle.write(_ENCRYPTION_MAGIC)
        output_handle.write(nonce)
        for chunk in iter(lambda: input_handle.read(1024 * 1024), b""):
            output_handle.write(encryptor.update(chunk))
        output_handle.write(encryptor.finalize())
        output_handle.write(encryptor.tag)
    _secure_permissions(target)


def _decrypt_file(source: Path, target: Path, key: bytes) -> None:
    file_size = source.stat().st_size
    minimum = len(_ENCRYPTION_MAGIC) + _NONCE_SIZE + _TAG_SIZE
    if file_size < minimum:
        raise BackupError("Зашифрованный backup имеет неверный формат.")
    with source.open("rb") as input_handle:
        magic = input_handle.read(len(_ENCRYPTION_MAGIC))
        if magic != _ENCRYPTION_MAGIC:
            raise BackupError("Backup не содержит ожидаемый заголовок шифрования.")
        nonce = input_handle.read(_NONCE_SIZE)
        input_handle.seek(-_TAG_SIZE, os.SEEK_END)
        tag = input_handle.read(_TAG_SIZE)
        ciphertext_start = len(_ENCRYPTION_MAGIC) + _NONCE_SIZE
        ciphertext_length = file_size - ciphertext_start - _TAG_SIZE
        input_handle.seek(ciphertext_start)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        remaining = ciphertext_length
        with target.open("wb") as output_handle:
            while remaining > 0:
                chunk = input_handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise BackupError("Зашифрованный backup неожиданно оборвался.")
                output_handle.write(decryptor.update(chunk))
                remaining -= len(chunk)
            try:
                output_handle.write(decryptor.finalize())
            except Exception as exc:
                raise BackupError(
                    "Не удалось расшифровать backup: ключ неверен или файл повреждён."
                ) from exc
    _secure_permissions(target)


def _database_identity(url: URL) -> dict[str, Any]:
    return {
        "backend": url.get_backend_name(),
        "host": url.host or None,
        "port": url.port,
        "database": url.database or None,
    }


def _database_inventory(database_url: str) -> tuple[str | None, dict[str, int]]:
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        tables = set(inspector.get_table_names())
        counts: dict[str, int] = {}
        with runtime.engine.connect() as connection:
            for table_name in _INVENTORY_TABLES:
                if table_name in tables:
                    counts[table_name] = int(
                        connection.scalar(text(f'SELECT COUNT(*) FROM "{table_name}"')) or 0
                    )
        return current_revision(runtime.engine), counts
    finally:
        runtime.dispose()


def _postgres_environment(url: URL) -> dict[str, str]:
    environment = dict(os.environ)
    if url.host:
        environment["PGHOST"] = str(url.host)
    if url.port:
        environment["PGPORT"] = str(url.port)
    if url.username:
        environment["PGUSER"] = str(url.username)
    if url.password:
        environment["PGPASSWORD"] = str(url.password)
    if url.database:
        environment["PGDATABASE"] = str(url.database)
    sslmode = url.query.get("sslmode")
    if sslmode:
        environment["PGSSLMODE"] = str(sslmode)
    return environment


def _tool_path(explicit: str | None, default_name: str) -> str:
    candidate = explicit or os.getenv(default_name.upper() + "_BIN") or default_name
    resolved = shutil.which(candidate)
    if resolved:
        return resolved
    path = Path(candidate)
    if path.is_file():
        return str(path)
    raise BackupError(
        f"Не найден {default_name}. Установите PostgreSQL client tools или задайте {default_name.upper()}_BIN."
    )


def _run_pg_dump(url: URL, target: Path, pg_dump_bin: str | None = None) -> None:
    tool = _tool_path(pg_dump_bin or os.getenv("PG_DUMP_BIN"), "pg_dump")
    command = [
        tool,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--dbname",
        str(url.database or ""),
    ]
    with target.open("wb") as output_handle:
        process = subprocess.run(
            command,
            stdout=output_handle,
            stderr=subprocess.PIPE,
            env=_postgres_environment(url),
            timeout=900,
            check=False,
        )
    if process.returncode != 0:
        raise BackupError(f"pg_dump завершился с кодом {process.returncode}.")
    _secure_permissions(target)


def _validate_postgres_dump(path: Path, pg_restore_bin: str | None = None) -> None:
    tool = _tool_path(pg_restore_bin or os.getenv("PG_RESTORE_BIN"), "pg_restore")
    with path.open("rb") as input_handle:
        process = subprocess.run(
            [tool, "--list"],
            stdin=input_handle,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    if process.returncode != 0:
        raise BackupError("pg_restore не смог прочитать созданный backup.")


def _run_pg_restore(
    url: URL,
    source: Path,
    *,
    clean: bool,
    pg_restore_bin: str | None = None,
) -> None:
    tool = _tool_path(pg_restore_bin or os.getenv("PG_RESTORE_BIN"), "pg_restore")
    command = [
        tool,
        "--exit-on-error",
        "--no-owner",
        "--no-privileges",
        "--dbname",
        str(url.database or ""),
    ]
    if clean:
        command.extend(["--clean", "--if-exists"])
    with source.open("rb") as input_handle:
        process = subprocess.run(
            command,
            stdin=input_handle,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=_postgres_environment(url),
            timeout=900,
            check=False,
        )
    if process.returncode != 0:
        raise BackupError(f"pg_restore завершился с кодом {process.returncode}.")


def _backup_sqlite(url: URL, target: Path) -> None:
    source_path = url.database
    if not source_path or source_path == ":memory:":
        raise BackupError("Нельзя создать файловый backup для SQLite in-memory database.")
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    _secure_permissions(target)


def _restore_sqlite(source_path: Path, target_url: URL) -> None:
    target_path = target_url.database
    if not target_path or target_path == ":memory:":
        raise BackupError("RESTORE_DATABASE_URL должен указывать на SQLite-файл.")
    Path(target_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(target_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def backup_database(
    database_url: str,
    output_dir: str | Path,
    *,
    output_name: str | None = None,
    encryption_key: str | bytes | None = None,
    environment: str = "development",
    allow_unencrypted: bool = False,
    service_name: str = "ai-career-agent",
    app_version: str = "unknown",
    pg_dump_bin: str | None = None,
    pg_restore_bin: str | None = None,
) -> BackupResult:
    """Create a validated backup plus a secret-free manifest."""

    try:
        url = make_url(database_url)
    except Exception as exc:
        raise BackupError("DATABASE_URL имеет неверный формат.") from exc
    backend = url.get_backend_name()
    if backend not in {"sqlite", "postgresql"}:
        raise BackupError("Backup поддерживает только SQLite и PostgreSQL.")

    key = _decode_encryption_key(encryption_key)
    if environment == "production" and key is None and not allow_unencrypted:
        raise BackupError(
            "Production backup требует BACKUP_ENCRYPTION_KEY или явный --allow-unencrypted."
        )

    destination_dir = Path(output_dir).expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = output_name or f"ai-career-agent-{timestamp}"
    if Path(base_name).name != base_name:
        raise BackupError("Имя backup не должно содержать путь.")
    native_suffix = ".dump" if backend == "postgresql" else ".sqlite3"
    if not base_name.endswith(native_suffix):
        base_name += native_suffix
    final_name = base_name + (".enc" if key else "")
    final_path = destination_dir / final_name
    if final_path.exists():
        raise BackupError(f"Backup уже существует: {final_path.name}.")

    revision, table_counts = _database_inventory(database_url)
    plain_path = destination_dir / ("." + base_name + ".tmp")
    try:
        if backend == "postgresql":
            _run_pg_dump(url, plain_path, pg_dump_bin=pg_dump_bin)
            _validate_postgres_dump(plain_path, pg_restore_bin=pg_restore_bin)
        else:
            _backup_sqlite(url, plain_path)
        if key:
            _encrypt_file(plain_path, final_path, key)
        else:
            plain_path.replace(final_path)
            _secure_permissions(final_path)
    finally:
        if plain_path.exists():
            plain_path.unlink()

    manifest = {
        "format_version": _BACKUP_FORMAT_VERSION,
        "created_at": _utc_now(),
        "service": service_name,
        "app_version": app_version,
        "source": _database_identity(url),
        "database_revision": revision,
        "table_counts": table_counts,
        "backup_file": final_path.name,
        "encrypted": bool(key),
        "cipher": "AES-256-GCM" if key else None,
        "size_bytes": final_path.stat().st_size,
        "sha256": _sha256(final_path),
    }
    manifest_path = final_path.with_name(final_path.name + ".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _secure_permissions(manifest_path)
    return BackupResult(final_path, manifest_path, manifest)


def validate_backup(
    backup_path: str | Path,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    backup = Path(backup_path).expanduser().resolve()
    manifest_file = (
        Path(manifest_path).expanduser().resolve()
        if manifest_path
        else backup.with_name(backup.name + ".manifest.json")
    )
    if not backup.is_file() or not manifest_file.is_file():
        raise BackupError("Backup или manifest не найден.")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise BackupError("Manifest backup повреждён или имеет неверный формат.") from exc
    if manifest.get("format_version") != _BACKUP_FORMAT_VERSION:
        raise BackupError("Версия manifest backup не поддерживается.")
    if manifest.get("backup_file") != backup.name:
        raise BackupError("Manifest относится к другому backup-файлу.")
    if int(manifest.get("size_bytes") or -1) != backup.stat().st_size:
        raise BackupError("Размер backup не совпадает с manifest.")
    if manifest.get("sha256") != _sha256(backup):
        raise BackupError("Контрольная сумма backup не совпадает с manifest.")
    return manifest


def restore_database(
    backup_path: str | Path,
    target_database_url: str,
    *,
    manifest_path: str | Path | None = None,
    encryption_key: str | bytes | None = None,
    environment: str = "development",
    allow_production: bool = False,
    clean: bool = False,
    pg_restore_bin: str | None = None,
) -> RestoreResult:
    """Restore a validated backup and compare revision/table counts."""

    if environment == "production" and not allow_production:
        raise BackupError(
            "Restore в production заблокирован. Используйте отдельную тестовую базу или --allow-production."
        )
    manifest = validate_backup(backup_path, manifest_path)
    backup = Path(backup_path).expanduser().resolve()
    try:
        target_url = make_url(target_database_url)
    except Exception as exc:
        raise BackupError("RESTORE_DATABASE_URL имеет неверный формат.") from exc
    target_backend = target_url.get_backend_name()
    source_backend = str((manifest.get("source") or {}).get("backend") or "")
    if target_backend != source_backend:
        raise BackupError("Backend target database не совпадает с backup.")

    key = _decode_encryption_key(encryption_key)
    if manifest.get("encrypted") and key is None:
        raise BackupError("Для restore требуется BACKUP_ENCRYPTION_KEY.")

    temporary_path: Path | None = None
    source_path = backup
    try:
        if manifest.get("encrypted"):
            file_descriptor, temporary_name = tempfile.mkstemp(prefix="aca-restore-", suffix=".tmp")
            os.close(file_descriptor)
            temporary_path = Path(temporary_name)
            _secure_permissions(temporary_path)
            _decrypt_file(backup, temporary_path, key or b"")
            source_path = temporary_path

        if target_backend == "postgresql":
            _validate_postgres_dump(source_path, pg_restore_bin=pg_restore_bin)
            _run_pg_restore(
                target_url,
                source_path,
                clean=clean,
                pg_restore_bin=pg_restore_bin,
            )
        elif target_backend == "sqlite":
            _restore_sqlite(source_path, target_url)
        else:
            raise BackupError("Restore поддерживает только SQLite и PostgreSQL.")
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    revision, table_counts = _database_inventory(target_database_url)
    expected_revision = manifest.get("database_revision")
    expected_counts = {
        str(key): int(value)
        for key, value in dict(manifest.get("table_counts") or {}).items()
    }
    verified = revision == expected_revision and all(
        table_counts.get(name) == count for name, count in expected_counts.items()
    )
    if not verified:
        raise BackupError(
            "Restore завершён, но revision или контрольные количества строк не совпали."
        )
    return RestoreResult(
        target_backend=target_backend,
        database_revision=revision,
        table_counts=table_counts,
        verified=True,
    )


def prune_backups(
    output_dir: str | Path,
    *,
    retention_days: int,
    now_timestamp: float | None = None,
) -> list[Path]:
    """Delete old backup files and matching manifests from one directory."""

    if retention_days < 1:
        raise BackupError("retention_days должен быть не меньше 1.")
    directory = Path(output_dir).expanduser().resolve()
    if not directory.exists():
        return []
    now_value = datetime.now(timezone.utc).timestamp() if now_timestamp is None else now_timestamp
    threshold = now_value - retention_days * 86_400
    removed: list[Path] = []
    for path in directory.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix not in {".enc", ".dump", ".sqlite3", ".json"}:
            continue
        if path.stat().st_mtime >= threshold:
            continue
        path.unlink()
        removed.append(path)
    return removed

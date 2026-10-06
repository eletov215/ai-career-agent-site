#!/usr/bin/env python3
"""Upload an authenticated encrypted backup to S3-compatible presigned HTTPS URLs."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


_ENCRYPTION_MAGIC = b"ACAOPS1"
_NONCE_SIZE = 12
_TAG_SIZE = 16


class ExportError(RuntimeError):
    """Raised when an off-VM backup export is unsafe or fails."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ExportError(f"{name} is required for backup export.")
    return value


def validate_presigned_url(value: str) -> str:
    parsed = urlsplit((value or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ExportError("Backup export requires an HTTPS presigned object URL.")
    if parsed.username or parsed.password:
        raise ExportError("Credentials must not be embedded as URL userinfo.")
    return value.strip()


def _decode_encryption_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError, base64.binascii.Error) as exc:
        raise ExportError("BACKUP_ENCRYPTION_KEY must be URL-safe base64.") from exc
    if len(key) != 32:
        raise ExportError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes.")
    return key


def validate_encryption_envelope(backup: Path) -> None:
    file_size = backup.stat().st_size
    minimum = len(_ENCRYPTION_MAGIC) + _NONCE_SIZE + _TAG_SIZE
    if file_size < minimum:
        raise ExportError("Encrypted backup has an invalid or truncated envelope.")
    with backup.open("rb") as handle:
        magic = handle.read(len(_ENCRYPTION_MAGIC))
    if magic != _ENCRYPTION_MAGIC:
        raise ExportError("Backup does not contain the ACAOPS1 encrypted envelope.")


def authenticate_encrypted_backup(backup: Path, encryption_key: str) -> None:
    """Authenticate the AES-256-GCM envelope without persisting plaintext."""

    validate_encryption_envelope(backup)
    key = _decode_encryption_key(encryption_key)
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ModuleNotFoundError as exc:
        raise ExportError("cryptography is required to authenticate encrypted backups.") from exc

    file_size = backup.stat().st_size
    ciphertext_start = len(_ENCRYPTION_MAGIC) + _NONCE_SIZE
    ciphertext_length = file_size - ciphertext_start - _TAG_SIZE

    with backup.open("rb") as handle:
        handle.seek(len(_ENCRYPTION_MAGIC))
        nonce = handle.read(_NONCE_SIZE)
        handle.seek(-_TAG_SIZE, os.SEEK_END)
        tag = handle.read(_TAG_SIZE)
        handle.seek(ciphertext_start)

        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        remaining = ciphertext_length
        try:
            while remaining > 0:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ExportError("Encrypted backup ended unexpectedly.")
                decryptor.update(chunk)
                remaining -= len(chunk)
            decryptor.finalize()
        except InvalidTag as exc:
            raise ExportError("Backup AES-GCM authentication failed.") from exc


def verify_encrypted_backup(
    backup: Path,
    manifest: Path,
    *,
    encryption_key: str,
) -> dict[str, object]:
    backup = backup.resolve()
    manifest = manifest.resolve()
    if not backup.is_file() or not manifest.is_file():
        raise ExportError("Backup or manifest file does not exist.")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise ExportError("Backup manifest is invalid.") from exc
    if payload.get("encrypted") is not True or not backup.name.endswith(".enc"):
        raise ExportError("Only encrypted backup artifacts may leave the VM.")
    if payload.get("backup_file") != backup.name:
        raise ExportError("Manifest belongs to a different backup file.")
    if int(payload.get("size_bytes") or -1) != backup.stat().st_size:
        raise ExportError("Backup size does not match manifest.")
    if payload.get("sha256") != _sha256(backup):
        raise ExportError("Backup checksum does not match manifest.")

    authenticate_encrypted_backup(backup, encryption_key)
    return payload


def _upload(path: Path, url: str) -> None:
    command = [
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--proto",
        "=https",
        "--tlsv1.2",
        "--upload-file",
        str(path),
        url,
    ]
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExportError("HTTPS backup export timed out.") from exc.__class__()
    except OSError as exc:
        raise ExportError("HTTPS backup export could not start.") from exc.__class__()
    if process.returncode != 0:
        raise ExportError(f"HTTPS backup export failed with code {process.returncode}.")


def _artifact_path(root: Path, name: str) -> Path:
    if not name:
        raise ExportError("Backup export filename must not be empty.")
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ExportError("Backup export path must remain inside BACKUP_DIR.") from exc
    return candidate


def main() -> int:
    root = Path(os.getenv("BACKUP_DIR", "/var/backups/ai-career-agent")).resolve()
    backup = _artifact_path(root, _required_env("BACKUP_EXPORT_FILE"))
    manifest = _artifact_path(root, _required_env("BACKUP_EXPORT_MANIFEST"))
    backup_url = validate_presigned_url(_required_env("BACKUP_S3_PRESIGNED_URL"))
    manifest_url = validate_presigned_url(
        _required_env("BACKUP_S3_MANIFEST_PRESIGNED_URL")
    )
    encryption_key = _required_env("BACKUP_ENCRYPTION_KEY")

    verify_encrypted_backup(backup, manifest, encryption_key=encryption_key)
    _upload(backup, backup_url)
    _upload(manifest, manifest_url)
    print(json.dumps({"ok": True, "backup": backup.name, "manifest": manifest.name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

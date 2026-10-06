#!/usr/bin/env python3
"""Upload an encrypted backup and manifest to S3-compatible presigned HTTPS URLs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


class ExportError(RuntimeError):
    """Raised when an off-VM backup export is unsafe or fails."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_presigned_url(value: str) -> str:
    parsed = urlsplit((value or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise ExportError("Backup export requires an HTTPS presigned object URL.")
    if parsed.username or parsed.password:
        raise ExportError("Credentials must not be embedded as URL userinfo.")
    return value.strip()


def verify_encrypted_backup(backup: Path, manifest: Path) -> dict[str, object]:
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
    return payload


def _upload(path: Path, url: str) -> None:
    process = subprocess.run(
        [
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
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=1800,
        check=False,
    )
    if process.returncode != 0:
        raise ExportError(f"HTTPS backup export failed with code {process.returncode}.")


def _artifact_path(root: Path, name: str) -> Path:
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ExportError("Backup export path must remain inside BACKUP_DIR.") from exc
    return candidate


def main() -> int:
    root = Path(os.getenv("BACKUP_DIR", "/var/backups/ai-career-agent")).resolve()
    backup = _artifact_path(root, os.environ["BACKUP_EXPORT_FILE"])
    manifest = _artifact_path(root, os.environ["BACKUP_EXPORT_MANIFEST"])
    backup_url = validate_presigned_url(os.environ["BACKUP_S3_PRESIGNED_URL"])
    manifest_url = validate_presigned_url(os.environ["BACKUP_S3_MANIFEST_PRESIGNED_URL"])

    verify_encrypted_backup(backup, manifest)
    _upload(backup, backup_url)
    _upload(manifest, manifest_url)
    print(json.dumps({"ok": True, "backup": backup.name, "manifest": manifest.name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

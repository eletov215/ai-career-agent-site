#!/usr/bin/env python3
"""Upload an authenticated encrypted backup to S3-compatible presigned HTTPS URLs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


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


def _object_target_identity(value: str) -> tuple[str, str, int, str]:
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port or 443
    decoded_path = unquote(parsed.path)
    yandex_suffix = ".storage.yandexcloud.net"

    # Yandex Object Storage accepts both virtual-hosted and path-style aliases:
    #   https://<bucket>.storage.yandexcloud.net/<key>
    #   https://storage.yandexcloud.net/<bucket>/<key>
    # Canonicalize both to the same bucket/key identity so two presigned URLs
    # cannot accidentally overwrite the same remote object.
    if host.endswith(yandex_suffix) and host != "storage.yandexcloud.net":
        bucket = host[: -len(yandex_suffix)]
        key = decoded_path.lstrip("/")
        return ("yandex-object-storage", bucket, port, key)

    if host == "storage.yandexcloud.net":
        bucket_and_key = decoded_path.lstrip("/")
        bucket, separator, key = bucket_and_key.partition("/")
        if bucket and separator:
            return ("yandex-object-storage", bucket.lower(), port, key)

    return (scheme, host, port, decoded_path)


def validate_distinct_object_targets(backup_url: str, manifest_url: str) -> None:
    if _object_target_identity(backup_url) == _object_target_identity(manifest_url):
        raise ExportError("Backup and manifest must use distinct object targets.")


def _aws_quote(value: str) -> str:
    return quote(str(value), safe="-_.~")


def _canonical_query(parameters: dict[str, str]) -> str:
    return "&".join(
        f"{_aws_quote(name)}={_aws_quote(value)}"
        for name, value in sorted(parameters.items())
    )


def _sigv4_hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


def generate_presigned_put_url(
    bucket: str,
    object_key: str,
    access_key: str,
    secret_key: str,
    *,
    expires_seconds: int = 900,
    now: datetime | None = None,
) -> str:
    """Generate a short-lived Yandex Object Storage PUT URL without logging credentials."""

    bucket = (bucket or "").strip().lower()
    object_key = (object_key or "").lstrip("/")
    access_key = (access_key or "").strip()
    secret_key = secret_key or ""

    if (
        not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket)
        or ".." in bucket
    ):
        raise ExportError("BACKUP_S3_BUCKET is invalid.")
    if not object_key or len(object_key) > 1024 or "\x00" in object_key:
        raise ExportError("Object Storage key is invalid.")
    if not access_key or not secret_key:
        raise ExportError("Object Storage access credentials are required.")
    if expires_seconds < 60 or expires_seconds > 3600:
        raise ExportError("Presigned upload lifetime must be between 60 and 3600 seconds.")

    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)

    date_stamp = moment.strftime("%Y%m%d")
    amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
    region = "ru-central1"
    service = "s3"
    host = "storage.yandexcloud.net"
    canonical_uri = "/" + quote(
        f"{bucket}/{object_key}",
        safe="/-_.~",
    )
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    parameters = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{access_key}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_seconds),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_query = _canonical_query(parameters)
    canonical_request = (
        "PUT\n"
        f"{canonical_uri}\n"
        f"{canonical_query}\n"
        f"host:{host}\n\n"
        "host\n"
        "UNSIGNED-PAYLOAD"
    )
    string_to_sign = (
        "AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )
    signing_key = _sigv4_hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    signing_key = _sigv4_hmac(signing_key, region)
    signing_key = _sigv4_hmac(signing_key, service)
    signing_key = _sigv4_hmac(signing_key, "aws4_request")
    signature = hmac.new(
        signing_key,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"https://{host}{canonical_uri}?"
        f"{canonical_query}&X-Amz-Signature={signature}"
    )


def _object_key(prefix: str, filename: str) -> str:
    prefix = (prefix or "").strip().strip("/")
    if prefix:
        if len(prefix) > 128 or "\x00" in prefix or any(
            part in {"", ".", ".."} for part in prefix.split("/")
        ):
            raise ExportError("BACKUP_S3_OBJECT_PREFIX is invalid.")
        return f"{prefix}/{filename}"
    return filename


def _resolve_upload_urls(backup: Path, manifest: Path) -> tuple[str, str]:
    backup_url = (os.getenv("BACKUP_S3_PRESIGNED_URL") or "").strip()
    manifest_url = (os.getenv("BACKUP_S3_MANIFEST_PRESIGNED_URL") or "").strip()
    if bool(backup_url) != bool(manifest_url):
        raise ExportError("Both presigned upload URLs must be provided together.")

    if backup_url and manifest_url:
        backup_url = validate_presigned_url(backup_url)
        manifest_url = validate_presigned_url(manifest_url)
        validate_distinct_object_targets(backup_url, manifest_url)
        return backup_url, manifest_url

    bucket = _required_env("BACKUP_S3_BUCKET")
    access_key = _required_env("BACKUP_S3_ACCESS_KEY")
    secret_key = _required_env("BACKUP_S3_SECRET_KEY")
    prefix = os.getenv("BACKUP_S3_OBJECT_PREFIX", "field-test")
    try:
        expires_seconds = int(os.getenv("BACKUP_S3_PRESIGN_EXPIRES_SECONDS", "900"))
    except ValueError as exc:
        raise ExportError("BACKUP_S3_PRESIGN_EXPIRES_SECONDS must be an integer.") from exc

    backup_url = generate_presigned_put_url(
        bucket,
        _object_key(prefix, backup.name),
        access_key,
        secret_key,
        expires_seconds=expires_seconds,
    )
    manifest_url = generate_presigned_put_url(
        bucket,
        _object_key(prefix, manifest.name),
        access_key,
        secret_key,
        expires_seconds=expires_seconds,
    )
    validate_distinct_object_targets(backup_url, manifest_url)
    return backup_url, manifest_url


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
    except subprocess.TimeoutExpired:
        raise ExportError("HTTPS backup export timed out.") from None
    except OSError:
        raise ExportError("HTTPS backup export could not start.") from None
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
    backup_url, manifest_url = _resolve_upload_urls(backup, manifest)
    encryption_key = _required_env("BACKUP_ENCRYPTION_KEY")

    verify_encrypted_backup(backup, manifest, encryption_key=encryption_key)
    _upload(backup, backup_url)
    _upload(manifest, manifest_url)
    print(json.dumps({"ok": True, "backup": backup.name, "manifest": manifest.name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

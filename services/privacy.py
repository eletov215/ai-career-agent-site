"""PRIV-001 privacy export, deletion, and technical retention policy."""

from __future__ import annotations

import json
import re
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from config import AppSettings
from repositories.privacy import (
    PrivacyRepository,
    PrivacySnapshotConflictError,
)


class PrivacyAccountNotFoundError(LookupError):
    pass


class PrivacyReauthenticationRequiredError(PermissionError):
    pass


class PrivacyExportTooLargeError(ValueError):
    pass


class PrivacyOwnershipIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PrivacyExportArtifact:
    filename: str
    content: bytes
    counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    pending_account_days: int
    auth_artifact_days: int
    audit_days: int
    orphan_asset_days: int


_CONTENT_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
}

_SENSITIVE_KEY_PARTS = {
    "access_token",
    "refresh_token",
    "authorization",
    "password",
    "secret",
    "client_secret",
    "code_verifier",
    "device_code",
    "user_code",
    "saml_response",
    "assertion",
    "id_token",
    "session_token",
    "browser_state",
}
_JWT_RE = re.compile(r"^[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}$")
_OPAQUE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_~+./=-]{64,}$")


def _utc_iso(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds")


def _safe_zip_component(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "item"
    decoded = unquote(text)
    if (
        decoded in {".", ".."}
        or "/" in decoded
        or "\\" in decoded
        or decoded.startswith("~")
        or ":" in decoded
        or any(ord(ch) < 32 for ch in decoded)
    ):
        import hashlib

        return "item-" + hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", decoded)[:96].strip("._")
    return cleaned or "item"


def _scrub_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return value
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port:
        host = f"{host}:{parts.port}"
    safe_segments: list[str] = []
    for raw in parts.path.split("/"):
        decoded = unquote(raw)
        lowered = decoded.casefold()
        if any(marker in lowered for marker in ("token", "secret", "password", "code_verifier")):
            safe_segments.append("redacted")
        elif _JWT_RE.match(decoded) or _OPAQUE_TOKEN_RE.match(decoded):
            safe_segments.append("redacted")
        else:
            safe_segments.append(quote(decoded, safe="-._~:@"))
    safe_path = "/".join(safe_segments)
    return urlunsplit((parts.scheme.lower(), host, safe_path, "", ""))


def _sanitize_provider_value(value: Any, *, key_hint: str = "") -> Any:
    normalized_key = key_hint.casefold().replace("-", "_")
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return None
    if normalized_key in {"state", "code"}:
        return None
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            sanitized = _sanitize_provider_value(item, key_hint=str(key))
            if sanitized is not None:
                cleaned[str(key)] = sanitized
        return cleaned
    if isinstance(value, list):
        return [
            sanitized
            for item in value
            if (sanitized := _sanitize_provider_value(item, key_hint=key_hint)) is not None
        ]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower().startswith("bearer "):
            return "[redacted]"
        if _JWT_RE.match(stripped) or _OPAQUE_TOKEN_RE.match(stripped):
            return "[redacted]"
        if stripped.startswith(("http://", "https://")):
            return _scrub_url(stripped)
        return value
    return value


def _sanitize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    for connection in snapshot.get("oauth_connections", []):
        if isinstance(connection, dict):
            profile = connection.get("profile")
            if isinstance(profile, (dict, list)):
                connection["profile"] = _sanitize_provider_value(profile)
            else:
                connection["profile"] = {}
    return snapshot


class PrivacyService:
    """Technical privacy controls; legal policy wording remains LEGAL-001."""

    def __init__(self, repository: PrivacyRepository, settings: AppSettings) -> None:
        self.repository = repository
        self.settings = settings

    @property
    def retention_policy(self) -> RetentionPolicy:
        return RetentionPolicy(
            pending_account_days=self.settings.privacy_pending_account_retention_days,
            auth_artifact_days=self.settings.privacy_auth_artifact_retention_days,
            audit_days=self.settings.privacy_audit_retention_days,
            orphan_asset_days=self.settings.privacy_orphan_asset_retention_days,
        )

    def export_user_data(
        self,
        user_id: str,
        *,
        expected_password_hash: str,
        now: int | None = None,
    ) -> PrivacyExportArtifact:
        timestamp = int(time.time() if now is None else now)
        try:
            exported = self.repository.export_snapshot(
                user_id,
                expected_password_hash=expected_password_hash,
            )
        except PrivacySnapshotConflictError as exc:
            if exc.reason == "password_changed":
                raise PrivacyReauthenticationRequiredError(
                    "Пароль изменился. Повторите подтверждение."
                ) from exc
            raise PrivacyOwnershipIntegrityError(
                "Экспорт остановлен из-за несогласованности владельца данных."
            ) from exc
        if exported is None:
            raise PrivacyAccountNotFoundError("Аккаунт не найден.")
        snapshot, assets = exported
        snapshot = _sanitize_snapshot(snapshot)

        counts = {
            "oauth_connections": len(snapshot["oauth_connections"]),
            "career_profile_versions": len(snapshot["career_profile_versions"]),
            "resume_drafts": len(snapshot["resume_drafts"]),
            "resume_versions": len(snapshot["resume_versions"]),
            "resume_assets": len(snapshot["resume_assets"]),
            "resume_exports": len(snapshot["resume_exports"]),
            "resume_analysis_reports": len(snapshot.get("resume_analyses", [])),
            "resume_interview_sessions": len(snapshot.get("resume_interviews", [])),
            "cover_letters": len(snapshot.get("cover_letters", [])),
            "cover_letter_versions": len(snapshot.get("cover_letter_versions", [])),
            "cover_letter_proposals": len(snapshot.get("cover_letter_proposals", [])),
            "ai_consents": len(snapshot.get("ai_consents", [])),
            "saved_vacancies": len(snapshot.get("saved_vacancies", [])),
            "saved_vacancy_sources": len(snapshot.get("saved_vacancy_sources", [])),
            "saved_vacancy_trackers": len(snapshot.get("saved_vacancy_trackers", [])),
            "saved_vacancy_tracker_events": len(snapshot.get("saved_vacancy_tracker_events", [])),
            "vacancy_match_reports": len(snapshot.get("vacancy_matches", [])),
            "vacancy_match_series": len(snapshot.get("vacancy_match_series", [])),
            "auth_sessions": len(snapshot["authentication"]["sessions"]),
            "auth_tokens": len(snapshot["authentication"]["one_time_tokens"]),
        }
        manifest: dict[str, Any] = {
            "product": "AI Career Agent",
            "export_schema_version": 1,
            "generated_at": _utc_iso(timestamp),
            "format": "UTF-8 JSON plus original resume image assets",
            "secret_fields_omitted": [
                "password_hash",
                "auth_session_token_hash",
                "auth_token_hash",
                "oauth_access_token",
                "oauth_refresh_token",
                "oauth_browser_state",
                "oauth_code_verifier",
                "oauth_device_or_user_code",
            ],
            "counts": counts,
            "notes": [
                "PDF binaries are not stored server-side; only export metadata is included.",
                "Search result snapshots are service cache, not an owner profile, and are not included.",
                "This ZIP is not encrypted; protect or delete the downloaded copy yourself.",
            ],
        }
        manifest_bytes = json.dumps(
            manifest, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        data_bytes = json.dumps(
            snapshot, ensure_ascii=False, indent=2, sort_keys=True
        ).encode("utf-8")
        raw_estimate = len(manifest_bytes) + len(data_bytes) + sum(asset.byte_size for asset in assets)
        if raw_estimate > self.settings.privacy_export_max_raw_bytes:
            raise PrivacyExportTooLargeError(
                "Экспорт превышает допустимый размер. Обратитесь в поддержку."
            )

        with tempfile.SpooledTemporaryFile(
            max_size=self.settings.privacy_export_spool_max_bytes,
            mode="w+b",
        ) as output:
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", manifest_bytes)
                archive.writestr("data.json", data_bytes)
                for asset in assets:
                    extension = _CONTENT_EXTENSIONS.get(asset.content_type, ".bin")
                    path = PurePosixPath(
                        "assets",
                        _safe_zip_component(asset.draft_id),
                        f"{_safe_zip_component(asset.kind)}-{_safe_zip_component(asset.id)}{extension}",
                    ).as_posix()
                    archive.writestr(path, asset.data)
            output.flush()
            output.seek(0, 2)
            archive_size = output.tell()
            if archive_size > self.settings.privacy_export_max_archive_bytes:
                raise PrivacyExportTooLargeError(
                    "Готовый архив превышает допустимый размер. Обратитесь в поддержку."
                )
            output.seek(0)
            content = output.read()

        self.repository.record_export(counts, now=timestamp)
        filename = (
            "AI_Career_Agent_data_export_"
            f"{datetime.fromtimestamp(timestamp, tz=timezone.utc):%Y%m%d_%H%M%S}Z.zip"
        )
        return PrivacyExportArtifact(filename=filename, content=content, counts=counts)

    def delete_account(
        self,
        user_id: str,
        *,
        expected_password_hash: str,
        now: int | None = None,
    ) -> dict[str, int]:
        try:
            counts = self.repository.delete_account(
                user_id,
                expected_password_hash=expected_password_hash,
                now=now,
            )
        except PrivacySnapshotConflictError as exc:
            raise PrivacyReauthenticationRequiredError(
                "Пароль изменился. Повторите подтверждение удаления."
            ) from exc
        if counts is None:
            raise PrivacyAccountNotFoundError("Аккаунт не найден.")
        return counts

    def run_retention_cleanup(self, *, now: int | None = None) -> dict[str, int]:
        timestamp = int(time.time() if now is None else now)
        day = 24 * 60 * 60
        counts = self.repository.cleanup_retention(
            pending_account_cutoff=(
                timestamp - self.settings.privacy_pending_account_retention_days * day
            ),
            auth_artifact_cutoff=(
                timestamp - self.settings.privacy_auth_artifact_retention_days * day
            ),
            audit_cutoff=(timestamp - self.settings.privacy_audit_retention_days * day),
            orphan_asset_cutoff=(
                timestamp - self.settings.privacy_orphan_asset_retention_days * day
            ),
            batch_size=self.settings.privacy_cleanup_batch_size,
            now=timestamp,
        )
        from repositories.ai import AIRepository
        ai_counts = AIRepository(self.repository.engine).cleanup(now=timestamp, limit=self.settings.privacy_cleanup_batch_size)
        counts.update({"ai_"+key: value for key,value in ai_counts.items()})
        return counts

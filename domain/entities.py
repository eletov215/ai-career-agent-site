"""Immutable application records detached from SQLAlchemy sessions.

The repository layer converts ORM rows to these small records before returning
anything to Flask routes or application services.  This keeps transaction and
persistence concerns out of the web layer and provides stable contracts for the
future account, profile, matching, and synchronization packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class UserRecord:
    """First-party AI Career Agent identity prepared for AUTH-001."""

    id: str
    email: str | None
    normalized_email: str | None
    display_name: str | None
    status: str
    email_verified_at: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class OAuthConnectionRecord:
    """One external OAuth identity detached from the persistence model."""

    id: str
    provider: str
    external_user_id: str
    user_id: str | None
    display_name: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    access_token: str
    refresh_token: str | None
    expires_at: int | None
    profile_json: str
    created_at: int
    updated_at: int

    def as_legacy_mapping(self) -> dict[str, Any]:
        """Return the mapping expected by the current OAuth/dashboard code.

        DATA-002 changes persistence without changing the established session,
        token-refresh, or template contracts.  AUTH-001/AUTH-002 will replace
        this compatibility mapping after first-party accounts are introduced.
        """

        common: dict[str, Any] = {
            "external_user_id": self.external_user_id,
            "email": self.email,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "profile_json": self.profile_json,
            "updated_at": self.updated_at,
        }
        if self.provider == "superjob":
            try:
                legacy_user_id: int | str = int(self.external_user_id)
            except ValueError:
                legacy_user_id = self.external_user_id
            common.update(
                {
                    "user_id": legacy_user_id,
                    "name": self.display_name or "Пользователь SuperJob",
                }
            )
        elif self.provider == "headhunter":
            common.update(
                {
                    "user_id": self.external_user_id,
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                }
            )
        return common


@dataclass(frozen=True, slots=True)
class VacancyRecord:
    """Canonical vacancy independent of any one provider publication."""

    id: str
    fingerprint: str | None
    title: str
    company: str | None
    salary_from: float | None
    salary_to: float | None
    currency: str | None
    location: str | None
    remote: bool
    schedule: str | None
    employment: str | None
    experience: str | None
    description: str | None
    requirements: str | None
    published_at: str | None
    is_active: bool
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One provider publication linked to a canonical vacancy."""

    id: int
    vacancy_id: str
    source: str
    external_id: str
    title: str
    company: str | None
    salary_from: float | None
    salary_to: float | None
    currency: str | None
    location: str | None
    remote: bool
    schedule: str | None
    employment: str | None
    experience: str | None
    description: str | None
    requirements: str | None
    published_at: str | None
    url: str | None
    search_text: str | None
    raw_json: str | None
    source_status: str
    source_modified_at: str | None
    closed_at: int | None
    closed_reason: str | None
    last_seen_run_id: str | None
    first_seen_at: int
    last_seen_at: int
    fetched_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class SyncCheckpointRecord:
    """Durable incremental watermark and retry state for one source."""

    source: str
    watermark_at: int | None
    pending_from_at: int | None
    pending_to_at: int | None
    pending_offset: int | None
    pending_limit: int | None
    pending_total: int | None
    last_success_run_id: str | None
    last_success_at: int | None
    last_cleanup_at: int | None
    consecutive_failures: int
    next_retry_at: int | None
    created_at: int
    updated_at: int

    @property
    def has_pending_window(self) -> bool:
        return bool(
            self.pending_to_at is not None
            and self.pending_offset is not None
            and self.pending_limit is not None
        )

    def public_summary(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "watermark_at": self.watermark_at,
            "pending": self.has_pending_window,
            "pending_from_at": self.pending_from_at,
            "pending_to_at": self.pending_to_at,
            "pending_offset": self.pending_offset,
            "pending_total": self.pending_total,
            "last_success_at": self.last_success_at,
            "last_cleanup_at": self.last_cleanup_at,
            "consecutive_failures": self.consecutive_failures,
            "next_retry_at": self.next_retry_at,
        }


@dataclass(frozen=True, slots=True)
class SyncWorkerRecord:
    """Heartbeat of a synchronization worker process."""

    id: str
    source: str
    status: str
    current_run_id: str | None
    started_at: int
    heartbeat_at: int
    details_json: str | None
    created_at: int
    updated_at: int

    def public_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "status": self.status,
            "current_run_id": self.current_run_id,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
        }


@dataclass(frozen=True, slots=True)
class SyncRunRecord:
    """Persisted status of one provider synchronization attempt."""

    id: str
    source: str
    trigger: str
    status: str
    started_at: int
    finished_at: int | None
    target: int | None
    processed: int
    saved: int
    cursor: str | None
    error_type: str | None
    error_message: str | None
    details_json: str | None
    created_at: int
    updated_at: int

    def public_summary(self) -> dict[str, Any]:
        """Return the existing diagnostic payload without database internals."""

        return {
            "id": self.id,
            "source": self.source,
            "trigger": self.trigger,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "target": self.target,
            "processed": self.processed,
            "saved": self.saved,
            "cursor": self.cursor,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

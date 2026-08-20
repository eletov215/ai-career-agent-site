"""Persistent, minimised source health telemetry for SEARCH-005.

Only provider key, outcome, bounded latency, safe error category/class and
aggregate cache metadata are stored. Request arguments, response bodies,
credentials and user identifiers are deliberately outside this contract.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseRuntime
from domain.source_health import SourceHealthRecord, SourceHealthView
from repositories.source_health import SourceHealthRepository


PROVIDERS = ("hh", "superjob", "reed", "trudvsem")
PROVIDER_TITLES = {
    "hh": "HeadHunter",
    "superjob": "SuperJob",
    "reed": "Reed.co.uk",
    "trudvsem": "Работа России",
}
_AVAILABILITY = {
    "unknown",
    "available",
    "cached",
    "degraded",
    "auth_required",
    "temporarily_unavailable",
    "disabled",
}
_SAFE_DETAIL_KEYS = {
    "sync_status",
    "worker_alive",
    "worker_status",
    "cache_stale",
}
_REPOSITORY: SourceHealthRepository | None = None


def configure_source_health(database: DatabaseRuntime) -> None:
    global _REPOSITORY
    _REPOSITORY = SourceHealthRepository(database)


def _repository() -> SourceHealthRepository:
    if _REPOSITORY is None:
        raise RuntimeError("Source health repository is not configured")
    return _REPOSITORY


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().casefold()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _configured(provider: str) -> tuple[bool, str]:
    """Return only boolean/safe reason; never return configuration values."""

    key = str(provider or "").strip().casefold()
    if key == "hh":
        if not _env_bool("HH_SEARCH_ENABLED", True):
            return False, "disabled"
        if str(os.getenv("HH_SEARCH_ENABLED", "")).strip():
            return True, "configured"
        present = bool(os.getenv("HH_USER_AGENT") or os.getenv("HH_CLIENT_ID"))
        return (present, "configured" if present else "missing_configuration")
    if key == "superjob":
        if not _env_bool("SUPERJOB_SEARCH_ENABLED", True):
            return False, "disabled"
        present = bool(
            os.getenv("SUPERJOB_SECRET_KEY")
            or os.getenv("SUPERJOB_CLIENT_SECRET")
            or os.getenv("SUPERJOB_CLIENT_ID")
        )
        return (present, "configured" if present else "missing_api_key")
    if key == "reed":
        if not _env_bool("REED_SEARCH_ENABLED", True):
            return False, "disabled"
        present = bool(os.getenv("REED_API_KEY"))
        return (present, "configured" if present else "missing_api_key")
    if key == "trudvsem":
        enabled = _env_bool("TRUDVSEM_SYNC_ENABLED", True)
        return (enabled, "configured" if enabled else "disabled")
    return False, "unknown_provider"


def _bounded_int(value: Any, *, maximum: int = 2_147_483_647) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(int(round(float(value))), maximum))
    except (TypeError, ValueError, OverflowError):
        return None


def _error_fields(
    error: BaseException | None,
    *,
    error_code: str | None = None,
    status_code: int | None = None,
    timeout: bool = False,
) -> tuple[str | None, str | None, str]:
    code = str(error_code or (type(error).__name__ if error is not None else "ProviderError"))[:120]
    timed_out = timeout or isinstance(error, TimeoutError) or "timeout" in code.casefold()
    if timed_out:
        return "timeout", code, "temporarily_unavailable"
    if status_code in {401, 403}:
        return "authorization", code, "auth_required"
    if status_code == 429:
        return "rate_limit", code, "degraded"
    if status_code is not None and int(status_code) >= 500:
        return "upstream", code, "temporarily_unavailable"
    return "provider_error", code, "degraded"


def _safe_details(details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    safe: dict[str, object] = {}
    for key in _SAFE_DETAIL_KEYS:
        if key not in details:
            continue
        value = details[key]
        if isinstance(value, bool):
            safe[key] = value
        elif key.endswith("status"):
            safe[key] = str(value)[:32]
    if not safe:
        return None
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_observation(
    provider: str,
    *,
    success: bool,
    latency_ms: int | float | None = None,
    error: BaseException | None = None,
    error_code: str | None = None,
    status_code: int | None = None,
    timeout: bool = False,
    cache_item_count: int | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    """Persist one safe current-state observation; failures are non-gating."""

    key = str(provider or "").strip().casefold()
    if key not in PROVIDERS or not _env_bool("SOURCE_HEALTH_RECORDING_ENABLED", True):
        return False
    configured, _reason = _configured(key)
    latency = _bounded_int(latency_ms, maximum=600_000)
    cache_count = _bounded_int(cache_item_count)
    if success:
        availability = "available" if configured else "disabled"
        category = None
        code = None
    else:
        category, code, availability = _error_fields(
            error,
            error_code=error_code,
            status_code=status_code,
            timeout=timeout,
        )
        if not configured:
            availability = "disabled"
    try:
        _repository().record_observation(
            provider=key,
            configured=configured,
            success=success,
            availability=availability,
            latency_ms=latency,
            error_category=category,
            error_code=code,
            cache_item_count=cache_count,
            details_json=_safe_details(details),
        )
        return True
    except (SQLAlchemyError, RuntimeError):
        return False


def record_cache_observation(provider: str, count: int) -> bool:
    key = str(provider or "").strip().casefold()
    if key not in PROVIDERS or not _env_bool("SOURCE_HEALTH_RECORDING_ENABLED", True):
        return False
    configured, _reason = _configured(key)
    safe_count = _bounded_int(count)
    if safe_count is None:
        return False
    try:
        existing = _repository().get(key)
        availability = (
            existing.availability
            if existing is not None
            else ("unknown" if configured else "disabled")
        )
        _repository().record_cache(
            provider=key,
            configured=configured,
            availability=availability,
            cache_item_count=safe_count,
        )
        return True
    except (SQLAlchemyError, RuntimeError):
        return False


def list_health_views(*, now: int | None = None) -> list[SourceHealthView]:
    current = int(time.time()) if now is None else int(now)
    try:
        stale_after = max(60, min(int(os.getenv("SOURCE_HEALTH_STALE_SECONDS", "900")), 86_400))
    except ValueError:
        stale_after = 900
    rows: dict[str, SourceHealthRecord] = {}
    try:
        rows = {row.provider: row for row in _repository().list() if row.provider in PROVIDERS}
    except (SQLAlchemyError, RuntimeError):
        rows = {}

    views: list[SourceHealthView] = []
    for key in PROVIDERS:
        configured, reason = _configured(key)
        row = rows.get(key)
        last_attempt = row.last_attempt_at if row else None
        stale = bool(last_attempt is not None and current - int(last_attempt) > stale_after)
        availability = row.availability if row else ("unknown" if configured else "disabled")
        if availability not in _AVAILABILITY:
            availability = "unknown"
        views.append(
            SourceHealthView(
                provider=key,
                title=PROVIDER_TITLES[key],
                availability=availability,
                configured=configured,
                configured_reason=reason,
                last_attempt_at=last_attempt,
                last_success_at=row.last_success_at if row else None,
                last_failure_at=row.last_failure_at if row else None,
                last_latency_ms=row.last_latency_ms if row else None,
                consecutive_failures=row.consecutive_failures if row else 0,
                error_category=row.error_category if row else None,
                error_code=row.error_code if row else None,
                cache_observed_at=row.cache_observed_at if row else None,
                cache_item_count=row.cache_item_count if row else None,
                stale=stale,
                stale_after_seconds=stale_after,
            )
        )
    return views

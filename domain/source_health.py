"""Safe detached source-health records for SEARCH-005."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceHealthRecord:
    provider: str
    availability: str
    configured: bool
    last_attempt_at: int | None
    last_success_at: int | None
    last_failure_at: int | None
    last_latency_ms: int | None
    consecutive_failures: int
    error_category: str | None
    error_code: str | None
    cache_observed_at: int | None
    cache_item_count: int | None
    details_json: str | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class SourceHealthView:
    provider: str
    title: str
    availability: str
    configured: bool
    configured_reason: str
    last_attempt_at: int | None
    last_success_at: int | None
    last_failure_at: int | None
    last_latency_ms: int | None
    consecutive_failures: int
    error_category: str | None
    error_code: str | None
    cache_observed_at: int | None
    cache_item_count: int | None
    stale: bool
    stale_after_seconds: int

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "title": self.title,
            "availability": self.availability,
            "configured": self.configured,
            "configured_reason": self.configured_reason,
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "last_latency_ms": self.last_latency_ms,
            "consecutive_failures": self.consecutive_failures,
            "error_category": self.error_category,
            "error_code": self.error_code,
            "cache_observed_at": self.cache_observed_at,
            "cache_item_count": self.cache_item_count,
            "stale": self.stale,
            "stale_after_seconds": self.stale_after_seconds,
        }

"""Attach persistent SEARCH-005 recording to existing OPS provider metrics."""

from __future__ import annotations

from typing import Any


def install_source_health_instrumentation() -> bool:
    """Idempotently wrap OPS_STATE.record_provider.

    The wrapper is deliberately fail-soft: persistent telemetry can never change
    a provider/search result.
    """

    try:
        from observability import OPS_STATE
    except ModuleNotFoundError as exc:
        # Lightweight local verification environments may omit Flask, which is
        # imported by observability. GitHub/production install Flask and execute
        # the real hook. Keeping this helper import-safe lets pure service tests
        # run without weakening the runtime path.
        if exc.name == "flask":
            return True
        raise
    from services.source_health import record_observation

    if getattr(OPS_STATE, "_source_health_instrumented", False):
        return True

    original = OPS_STATE.record_provider

    def wrapped_record_provider(
        *,
        provider: str,
        operation: str,
        success: bool,
        duration_ms: float,
        status_code: int | None = None,
        error_type: str | None = None,
        timeout: bool = False,
        **kwargs: Any,
    ) -> None:
        original(
            provider=provider,
            operation=operation,
            success=success,
            duration_ms=duration_ms,
            status_code=status_code,
            error_type=error_type,
            timeout=timeout,
            **kwargs,
        )
        try:
            record_observation(
                provider,
                success=success,
                latency_ms=duration_ms,
                error_code=error_type,
                status_code=status_code,
                timeout=timeout,
            )
        except Exception:
            # SEARCH-005 telemetry is explicitly non-gating.
            return

    OPS_STATE.record_provider = wrapped_record_provider  # type: ignore[method-assign]
    setattr(OPS_STATE, "_source_health_instrumented", True)
    return True

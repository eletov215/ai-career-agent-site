from __future__ import annotations

from typing import Any


class BenchmarkError(RuntimeError):
    """Base error for benchmark configuration or execution failures."""


class ConfigurationError(BenchmarkError):
    """Raised when benchmark configuration is invalid."""


class DatasetError(BenchmarkError):
    """Raised when the benchmark dataset violates its contract."""


class ProviderError(BenchmarkError):
    """Raised when a provider adapter cannot return a usable response.

    ``diagnostics`` must remain safe to persist in benchmark evidence. Raw
    provider bodies, credentials, request headers and refusal text are never
    stored here.
    """

    def __init__(self, message: str, *, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = dict(diagnostics or {})

"""Provider-neutral AI-001 contracts. Request/response bodies are never repr'd."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol

PROVIDER = "yandex-alice-ai-llm"
CONTRACT = "grounded-v2.6.1"
TASKS = ("resume_analysis", "vacancy_match", "cover_letter", "interview_questions")
# Deliberate product boundary: a flag cannot bypass unresolved legal/consent work.
REAL_DATA_SUPPORTED = False

@dataclass(frozen=True, slots=True)
class AIRequest:
    user_id: str = field(repr=False)
    idempotency_key: str = field(repr=False)
    fixture_id: str

@dataclass(frozen=True, slots=True)
class ProviderCall:
    request_id: str
    task: str
    language: str
    messages: list[dict[str, str]] = field(repr=False)
    schema: dict[str, Any] = field(repr=False)
    max_output_tokens: int
    timeout_seconds: float

@dataclass(frozen=True, slots=True)
class ProviderResponse:
    content: str = field(repr=False)
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str = "stop"

class ProviderError(RuntimeError):
    """Only allowlisted codes cross the transport boundary, never raw errors."""
    CODES = frozenset(("rate_limited", "upstream_error", "permission_denied", "invalid_request",
                      "timeout_unknown", "transport_unknown", "invalid_envelope", "refusal", "configuration"))
    def __init__(self, code: str, *, retryable: bool = False, unknown: bool = True):
        self.code = code if code in self.CODES else "transport_unknown"
        self.retryable = bool(retryable and self.code in {"rate_limited", "upstream_error"})
        self.unknown = unknown
        super().__init__(self.code)

class AIProvider(Protocol):
    provider_id: str
    def generate(self, call: ProviderCall) -> ProviderResponse: ...

@dataclass(frozen=True, slots=True)
class AIResult:
    status: str
    reason: str
    request_id: str | None = None
    content: dict[str, Any] | None = field(default=None, repr=False)
    commercial_action_consumed: bool = False

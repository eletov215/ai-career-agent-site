from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceFact:
    fact_id: str
    text: str
    kind: str


@dataclass(frozen=True)
class GroundingRequirement:
    requirement_id: str
    any_of: tuple[str, ...]


@dataclass(frozen=True)
class ForbiddenClaim:
    claim_id: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class MatchRequirement:
    requirement_id: str
    importance: str
    weight: int
    expected_status: str
    candidate_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    task: str
    language: str
    synthetic: bool
    schema_path: Path
    messages: tuple[dict[str, str], ...]
    source_facts: tuple[SourceFact, ...]
    required_paths: tuple[str, ...]
    required_evidence_ids: tuple[str, ...]
    grounding_requirements: tuple[GroundingRequirement, ...]
    forbidden_claims: tuple[ForbiddenClaim, ...]
    generated_numeric_paths: tuple[str, ...]
    required_unverified_evidence_ids: tuple[str, ...]
    required_caveat_evidence_ids: tuple[str, ...]
    match_requirements: tuple[MatchRequirement, ...]
    manual_rubric: tuple[str, ...]
    tags: tuple[str, ...]
    source_path: Path


@dataclass(frozen=True)
class ProviderResponse:
    content: Any
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    adapter: str
    enabled: bool
    options: dict[str, Any]

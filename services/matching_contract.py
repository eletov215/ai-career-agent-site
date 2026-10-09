"""AI004-M03: deterministic requirement set and strict model-output schema.

This module does not call a provider, give AI access to personal data, or
activate matching. It uses the canonical M01 projections, which MUST have been
obtained through owner-qualified PROF-003/JOB-001 reads. A caller must also
establish from the original saved snapshot that requirements were not
truncated, before explicitly setting source_complete=True.

Employer requirements are pinned BEFORE the AI classification response: a
model cannot omit an inconvenient requirement, set weights, or invent scores.
The conservative v1 extractor supports only explicit requirements, separated
by newlines or semicolons. Other job descriptions are NOT scoreable yet.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from domain.vacancy_match import MATCH_VERSION, MAX_REQUIREMENTS
from services.matching_prefilter import PrefilterError, _verify_projection

CLASSIFICATION_VERSION = "ai004-grounded-classification-v1"
REQUIREMENT_POLICY_VERSION = "ai004-explicit-requirements-v1"
WEIGHT_POLICY_VERSION = "ai004-mandatory2-preferred1-v1"
MAX_REQUIREMENT_CHARS = 512
MAX_PROVIDER_OUTPUT_BYTES = 90_000
MAX_QUOTE_CHARS = 240
MAX_CANDIDATE_REFERENCES = 3

_SPLIT = re.compile(r"[^;\r\n]+")
_BULLET = re.compile(r"^(?:[-*\u2022]\s*|[0-9]{1,2}[.)]\s+)")
_PREFERRED = re.compile(
    r"(?:\bpreferred\b|\boptional\b|\bbonus\b|nice to have|"
    r"would be a plus|\bжелательно\b|\bприветствуется\b|"
    r"будет плюсом|\bнеобязательно\b)",
    re.IGNORECASE,
)
_MANDATORY = re.compile(
    r"(?:\bmust\b|\brequired\b|\bmandatory\b|"
    r"\bобязательно\b|\bнеобходимо\b|\bтребуется\b)",
    re.IGNORECASE,
)


class ClassificationContractError(ValueError):
    """Stable validation codes only; no source/model content in messages."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RequirementSpec:
    requirement_id: str
    source_id: str
    text: str = field(repr=False)
    importance: str = "mandatory"
    weight: int = 2


@dataclass(frozen=True, slots=True)
class ClassificationContract:
    source_hash: str
    resume_hash: str
    vacancy_hash: str
    requirements: tuple[RequirementSpec, ...] = field(repr=False)
    candidate_facts: tuple[dict[str, str], ...] = field(repr=False)
    schema: dict[str, Any] = field(repr=False)
    version: str = CLASSIFICATION_VERSION


def _requirements(text: str) -> tuple[RequirementSpec, ...]:
    if not isinstance(text, str) or not text.strip():
        raise ClassificationContractError("insufficient_requirements")
    items: list[RequirementSpec] = []
    seen: set[str] = set()
    for raw in _SPLIT.findall(text):
        statement = _BULLET.sub("", raw.strip()).strip()
        if not statement:
            continue
        if (len(statement) > MAX_REQUIREMENT_CHARS
                or any(ord(char) < 32 for char in statement)):
            raise ClassificationContractError("unsupported_requirements")
        normalized = " ".join(statement.casefold().split())
        if normalized in seen:
            # A duplicate must not inflate the denominator or quietly vanish.
            raise ClassificationContractError("ambiguous_requirements")
        seen.add(normalized)
        if len(items) >= MAX_REQUIREMENTS:
            raise ClassificationContractError("unsupported_requirements")
        importance = (
            "mandatory" if _MANDATORY.search(statement) else
            "preferred" if _PREFERRED.search(statement) else "mandatory"
        )
        items.append(RequirementSpec(
            requirement_id=f"req-{len(items) + 1:03d}",
            source_id="vacancy.requirements",
            text=statement,
            importance=importance,
            weight=2 if importance == "mandatory" else 1,
        ))
    if not items:
        raise ClassificationContractError("insufficient_requirements")
    return tuple(items)


def _schema(requirements: tuple[RequirementSpec, ...], fact_ids: list[str],
            source_hash: str) -> dict[str, Any]:
    evidence = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "quote"],
        "properties": {
            "id": {"type": "string", "enum": fact_ids},
            "quote": {"type": "string", "minLength": 2,
                      "maxLength": MAX_QUOTE_CHARS},
        },
    }
    classification = {
        "type": "object",
        "additionalProperties": False,
        "required": ["requirement_id", "status", "candidate_evidence"],
        "properties": {
            "requirement_id": {"type": "string",
                               "enum": [item.requirement_id for item in requirements]},
            "status": {"type": "string",
                       "enum": ["matched", "unverified", "mismatch"]},
            "candidate_evidence": {
                "type": "array", "minItems": 0,
                "maxItems": MAX_CANDIDATE_REFERENCES,
                "items": evidence,
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["contract_version", "source_hash", "classifications"],
        "properties": {
            "contract_version": {"type": "string",
                                 "enum": [CLASSIFICATION_VERSION]},
            "source_hash": {"type": "string", "enum": [source_hash]},
            "classifications": {
                "type": "array", "minItems": len(requirements),
                "maxItems": len(requirements), "items": classification,
            },
        },
    }


def build_classification_contract(
    resume: Mapping[str, Any],
    vacancy: Mapping[str, Any],
    *,
    source_complete: bool = False,
) -> ClassificationContract:
    """Pin source and requirement IDs before any future provider admission.

    source_complete=True is permitted ONLY after the owner-qualified saved
    vacancy reader checked snapshot.truncated_fields excludes requirements.
    Passing it without such a check is a caller bug, not an authorization.
    An absent/ambiguous explicit requirements field never produces a percentage.
    """
    if source_complete is not True:
        raise ClassificationContractError("source_completeness_unverified")
    try:
        _verify_projection(resume, kind="resume_version")
        _verify_projection(vacancy, kind="saved_vacancy")
    except (PrefilterError, ValueError, TypeError):
        raise ClassificationContractError("invalid_projection") from None

    items = _requirements(vacancy["fields"]["requirements"])
    facts = tuple({"id": row["id"], "text": row["text"]} for row in resume["facts"])
    fingerprint = _hash({
        "classification_version": CLASSIFICATION_VERSION,
        "requirement_policy": REQUIREMENT_POLICY_VERSION,
        "weight_policy": WEIGHT_POLICY_VERSION,
        "scoring_policy": MATCH_VERSION,
        "resume_hash": resume["content_hash"],
        "vacancy_hash": vacancy["content_hash"],
        "requirements": [{
            "id": item.requirement_id,
            "source_id": item.source_id,
            "text": item.text,
            "importance": item.importance,
            "weight": item.weight,
        } for item in items],
    })
    return ClassificationContract(
        source_hash=fingerprint,
        resume_hash=resume["content_hash"],
        vacancy_hash=vacancy["content_hash"],
        requirements=items,
        candidate_facts=facts,
        schema=_schema(items, [row["id"] for row in facts], fingerprint),
    )

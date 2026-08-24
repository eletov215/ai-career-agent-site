from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import DatasetError
from .models import BenchmarkCase, ForbiddenClaim, GroundingRequirement, SourceFact
from .schema import find_unsupported_keywords
from .util import canonical_json, sha256_text

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){10,}(?!\d)")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetError(f"Cannot read valid JSON from {path}: {exc}") from exc


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"{label} must be a non-empty string")
    return value.strip()


def load_dataset(manifest_path: Path) -> tuple[dict[str, Any], list[BenchmarkCase], str]:
    manifest_path = manifest_path.resolve()
    manifest = _load_json(manifest_path)
    if manifest.get("synthetic") is not True:
        raise DatasetError("Dataset manifest must explicitly declare synthetic=true")
    case_entries = manifest.get("cases")
    if not isinstance(case_entries, list) or not case_entries:
        raise DatasetError("Dataset manifest must contain at least one case")

    cases: list[BenchmarkCase] = []
    seen_ids: set[str] = set()
    fingerprint_payload: dict[str, Any] = {"manifest": manifest, "cases": []}

    for relative in case_entries:
        case_path = (manifest_path.parent / _require_non_empty_string(relative, "case path")).resolve()
        raw = _load_json(case_path)
        case_id = _require_non_empty_string(raw.get("case_id"), f"{case_path}: case_id")
        if case_id in seen_ids:
            raise DatasetError(f"Duplicate case_id: {case_id}")
        seen_ids.add(case_id)
        if raw.get("synthetic") is not True:
            raise DatasetError(f"{case_id}: synthetic must be true")

        serialized = canonical_json(raw)
        if _EMAIL_RE.search(serialized) or _PHONE_RE.search(serialized):
            raise DatasetError(f"{case_id}: fixture contains email/phone-like data; use synthetic facts without contact data")

        schema_rel = _require_non_empty_string(raw.get("schema"), f"{case_id}: schema")
        schema_path = (case_path.parent / schema_rel).resolve()
        schema = _load_json(schema_path)
        unsupported = find_unsupported_keywords(schema)
        if unsupported:
            raise DatasetError(f"{case_id}: unsupported schema keywords: {'; '.join(unsupported)}")

        messages_raw = raw.get("messages")
        if not isinstance(messages_raw, list) or not messages_raw:
            raise DatasetError(f"{case_id}: messages must be a non-empty list")
        messages: list[dict[str, str]] = []
        for index, message in enumerate(messages_raw):
            if not isinstance(message, dict):
                raise DatasetError(f"{case_id}: messages[{index}] must be an object")
            role = _require_non_empty_string(message.get("role"), f"{case_id}: messages[{index}].role")
            content = _require_non_empty_string(message.get("content"), f"{case_id}: messages[{index}].content")
            if role not in {"system", "user", "assistant"}:
                raise DatasetError(f"{case_id}: unsupported role {role!r}")
            messages.append({"role": role, "content": content})

        facts: list[SourceFact] = []
        fact_ids: set[str] = set()
        for fact in raw.get("source_facts", []):
            fact_id = _require_non_empty_string(fact.get("id"), f"{case_id}: source fact id")
            if fact_id in fact_ids:
                raise DatasetError(f"{case_id}: duplicate source fact id {fact_id}")
            fact_ids.add(fact_id)
            facts.append(SourceFact(fact_id=fact_id, text=_require_non_empty_string(fact.get("text"), f"{case_id}: source fact text")))

        required_evidence_ids = tuple(raw.get("required_evidence_ids", []))
        unknown_required = sorted(set(required_evidence_ids) - fact_ids)
        if unknown_required:
            raise DatasetError(f"{case_id}: required evidence ids do not exist: {unknown_required}")

        grounding_requirements: list[GroundingRequirement] = []
        for item in raw.get("grounding_requirements", []):
            requirement_id = _require_non_empty_string(item.get("id"), f"{case_id}: grounding requirement id")
            any_of = tuple(_require_non_empty_string(term, f"{case_id}: grounding term") for term in item.get("any_of", []))
            if not any_of:
                raise DatasetError(f"{case_id}: grounding requirement {requirement_id} has no terms")
            grounding_requirements.append(GroundingRequirement(requirement_id=requirement_id, any_of=any_of))

        forbidden_claims: list[ForbiddenClaim] = []
        for item in raw.get("forbidden_claims", []):
            claim_id = _require_non_empty_string(item.get("id"), f"{case_id}: forbidden claim id")
            terms = tuple(_require_non_empty_string(term, f"{case_id}: forbidden term") for term in item.get("terms", []))
            if not terms:
                raise DatasetError(f"{case_id}: forbidden claim {claim_id} has no terms")
            forbidden_claims.append(ForbiddenClaim(claim_id=claim_id, terms=terms))

        case = BenchmarkCase(
            case_id=case_id,
            task=_require_non_empty_string(raw.get("task"), f"{case_id}: task"),
            language=_require_non_empty_string(raw.get("language"), f"{case_id}: language"),
            synthetic=True,
            schema_path=schema_path,
            messages=tuple(messages),
            source_facts=tuple(facts),
            required_paths=tuple(raw.get("required_paths", [])),
            required_evidence_ids=required_evidence_ids,
            grounding_requirements=tuple(grounding_requirements),
            forbidden_claims=tuple(forbidden_claims),
            generated_numeric_paths=tuple(raw.get("generated_numeric_paths", [])),
            manual_rubric=tuple(raw.get("manual_rubric", [])),
            tags=tuple(raw.get("tags", [])),
            source_path=case_path,
        )
        cases.append(case)
        fingerprint_payload["cases"].append(raw)

    fingerprint = sha256_text(canonical_json(fingerprint_payload))
    return manifest, cases, fingerprint

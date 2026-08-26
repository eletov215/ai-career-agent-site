from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import DatasetError
from .models import BenchmarkCase, ForbiddenClaim, GroundingRequirement, MatchRequirement, SourceFact
from .schema import find_unsupported_keywords
from .util import canonical_json, sha256_text

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){10,}(?!\d)")
_FACT_ID_RE = re.compile(r"^[a-z][0-9]+$")
_FACT_KINDS = {"candidate", "vacancy", "scenario"}
_MATCH_IMPORTANCE = {"mandatory", "preferred"}
_MATCH_STATUS = {"matched", "gap"}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetError(f"Cannot read valid JSON from {path}: {exc}") from exc


def _require_non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_id_list(values: Any, *, label: str, known_ids: set[str]) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, list) or not all(isinstance(item, str) and item for item in values):
        raise DatasetError(f"{label} must be a list of non-empty identifiers")
    result = tuple(values)
    unknown = sorted(set(result) - known_ids)
    if unknown:
        raise DatasetError(f"{label} contains unknown evidence ids: {unknown}")
    return result


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
        fact_kinds: dict[str, str] = {}
        for fact in raw.get("source_facts", []):
            fact_id = _require_non_empty_string(fact.get("id"), f"{case_id}: source fact id")
            if not _FACT_ID_RE.fullmatch(fact_id):
                raise DatasetError(f"{case_id}: source fact id must match {_FACT_ID_RE.pattern!r}: {fact_id!r}")
            if fact_id in fact_ids:
                raise DatasetError(f"{case_id}: duplicate source fact id {fact_id}")
            kind = _require_non_empty_string(fact.get("kind"), f"{case_id}: source fact kind")
            if kind not in _FACT_KINDS:
                raise DatasetError(f"{case_id}: unsupported source fact kind {kind!r}")
            fact_ids.add(fact_id)
            fact_kinds[fact_id] = kind
            facts.append(
                SourceFact(
                    fact_id=fact_id,
                    text=_require_non_empty_string(fact.get("text"), f"{case_id}: source fact text"),
                    kind=kind,
                )
            )

        required_evidence_ids = _validate_id_list(
            raw.get("required_evidence_ids", []),
            label=f"{case_id}: required_evidence_ids",
            known_ids=fact_ids,
        )
        required_unverified_evidence_ids = _validate_id_list(
            raw.get("required_unverified_evidence_ids", []),
            label=f"{case_id}: required_unverified_evidence_ids",
            known_ids=fact_ids,
        )
        required_caveat_evidence_ids = _validate_id_list(
            raw.get("required_caveat_evidence_ids", []),
            label=f"{case_id}: required_caveat_evidence_ids",
            known_ids=fact_ids,
        )

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

        match_requirements: list[MatchRequirement] = []
        seen_match_ids: set[str] = set()
        for item in raw.get("match_requirements", []):
            requirement_id = _require_non_empty_string(item.get("requirement_id"), f"{case_id}: match requirement id")
            if requirement_id in seen_match_ids:
                raise DatasetError(f"{case_id}: duplicate match requirement id {requirement_id}")
            seen_match_ids.add(requirement_id)
            if requirement_id not in fact_ids or fact_kinds.get(requirement_id) != "vacancy":
                raise DatasetError(f"{case_id}: match requirement {requirement_id} must reference a vacancy source fact")
            importance = _require_non_empty_string(item.get("importance"), f"{case_id}: match requirement importance")
            if importance not in _MATCH_IMPORTANCE:
                raise DatasetError(f"{case_id}: unsupported match importance {importance!r}")
            expected_status = _require_non_empty_string(item.get("expected_status"), f"{case_id}: expected match status")
            if expected_status not in _MATCH_STATUS:
                raise DatasetError(f"{case_id}: unsupported expected match status {expected_status!r}")
            weight_raw = item.get("weight", 2 if importance == "mandatory" else 1)
            if not isinstance(weight_raw, int) or isinstance(weight_raw, bool) or weight_raw <= 0:
                raise DatasetError(f"{case_id}: match requirement weight must be a positive integer")
            candidate_evidence_ids = _validate_id_list(
                item.get("candidate_evidence_ids", []),
                label=f"{case_id}: {requirement_id}.candidate_evidence_ids",
                known_ids=fact_ids,
            )
            if any(fact_kinds.get(identifier) != "candidate" for identifier in candidate_evidence_ids):
                raise DatasetError(f"{case_id}: {requirement_id}.candidate_evidence_ids must reference candidate facts")
            match_requirements.append(
                MatchRequirement(
                    requirement_id=requirement_id,
                    importance=importance,
                    weight=weight_raw,
                    expected_status=expected_status,
                    candidate_evidence_ids=candidate_evidence_ids,
                )
            )
        task = _require_non_empty_string(raw.get("task"), f"{case_id}: task")
        if task == "vacancy_match" and not match_requirements:
            raise DatasetError(f"{case_id}: vacancy_match requires match_requirements")
        if task != "vacancy_match" and match_requirements:
            raise DatasetError(f"{case_id}: match_requirements are only valid for vacancy_match")

        case = BenchmarkCase(
            case_id=case_id,
            task=task,
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
            required_unverified_evidence_ids=required_unverified_evidence_ids,
            required_caveat_evidence_ids=required_caveat_evidence_ids,
            match_requirements=tuple(match_requirements),
            manual_rubric=tuple(raw.get("manual_rubric", [])),
            tags=tuple(raw.get("tags", [])),
            source_path=case_path,
        )
        cases.append(case)
        fingerprint_payload["cases"].append(raw)

    fingerprint = sha256_text(canonical_json(fingerprint_payload))
    return manifest, cases, fingerprint

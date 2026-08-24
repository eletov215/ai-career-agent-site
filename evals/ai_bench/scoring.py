from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import BenchmarkCase
from .schema import validate_instance
from .util import flatten_text, get_path, iter_paths, normalize_text

_EVIDENCE_KEY = "evidence_ids"
_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?%?(?![\w])")


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_evidence_ids(value: Any) -> list[str]:
    collected: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == _EVIDENCE_KEY and isinstance(item, list):
                collected.extend(str(entry) for entry in item)
            else:
                collected.extend(_collect_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            collected.extend(_collect_evidence_ids(item))
    return collected


def _score_required_paths(content: Any, paths: tuple[str, ...]) -> tuple[float, list[str]]:
    if not paths:
        return 1.0, []
    missing: list[str] = []
    for path in paths:
        exists, value = get_path(content, path)
        if not exists or value in (None, "", [], {}):
            missing.append(path)
    return (len(paths) - len(missing)) / len(paths), missing


def _score_grounding_terms(case: BenchmarkCase, text: str) -> tuple[float, list[str]]:
    if not case.grounding_requirements:
        return 1.0, []
    normalized = normalize_text(text)
    missing: list[str] = []
    for requirement in case.grounding_requirements:
        if not any(normalize_text(term) in normalized for term in requirement.any_of):
            missing.append(requirement.requirement_id)
    return (len(case.grounding_requirements) - len(missing)) / len(case.grounding_requirements), missing


def _find_forbidden_claims(case: BenchmarkCase, text: str) -> list[str]:
    normalized = normalize_text(text)
    found: list[str] = []
    for claim in case.forbidden_claims:
        if any(normalize_text(term) in normalized for term in claim.terms):
            found.append(claim.claim_id)
    return found


def _unsupported_numbers(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    source_text = "\n".join(message["content"] for message in case.messages)
    source_text += "\n" + "\n".join(fact.text for fact in case.source_facts)
    allowed = {token.replace(",", ".") for token in _NUMBER_RE.findall(source_text)}
    generated_path_prefixes = tuple(case.generated_numeric_paths)
    unsupported: list[dict[str, str]] = []
    for path, value in iter_paths(content):
        if any(path == prefix or path.startswith(prefix + "[") or path.startswith(prefix + ".") for prefix in generated_path_prefixes):
            continue
        if isinstance(value, bool) or value is None:
            continue
        text = str(value)
        for token in _NUMBER_RE.findall(text):
            normalized = token.replace(",", ".")
            if normalized not in allowed:
                unsupported.append({"path": path, "value": token})
    return unsupported


def score_case(case: BenchmarkCase, content: Any, thresholds: dict[str, Any]) -> dict[str, Any]:
    schema = _load_schema(case.schema_path)
    schema_errors = validate_instance(content, schema)
    required_path_coverage, missing_paths = _score_required_paths(content, case.required_paths)

    evidence_ids = _collect_evidence_ids(content)
    known_fact_ids = {fact.fact_id for fact in case.source_facts}
    invalid_evidence_ids = sorted(set(evidence_ids) - known_fact_ids)
    evidence_precision = (
        (len(evidence_ids) - sum(1 for item in evidence_ids if item not in known_fact_ids)) / len(evidence_ids)
        if evidence_ids
        else (1.0 if not case.required_evidence_ids else 0.0)
    )
    referenced = set(evidence_ids)
    missing_required_evidence = sorted(set(case.required_evidence_ids) - referenced)
    evidence_recall = (
        (len(case.required_evidence_ids) - len(missing_required_evidence)) / len(case.required_evidence_ids)
        if case.required_evidence_ids
        else 1.0
    )

    flattened = flatten_text(content)
    grounding_term_coverage, missing_grounding_requirements = _score_grounding_terms(case, flattened)
    forbidden_claims = _find_forbidden_claims(case, flattened)
    unsupported_numbers = _unsupported_numbers(case, content)

    schema_compliance = 1.0 if not schema_errors else 0.0
    grounding_score = round((evidence_precision + evidence_recall + grounding_term_coverage) / 3.0, 6)
    quality_score = round(
        0.30 * schema_compliance
        + 0.20 * required_path_coverage
        + 0.30 * grounding_score
        + 0.20 * (1.0 if not forbidden_claims else 0.0),
        6,
    )

    min_required_path_coverage = float(thresholds.get("min_required_path_coverage", 1.0))
    min_grounding_score = float(thresholds.get("min_grounding_score", 0.85))
    min_quality_score = float(thresholds.get("min_quality_score", 0.85))
    max_forbidden_claims = int(thresholds.get("max_forbidden_claims", 0))
    max_invalid_evidence_ids = int(thresholds.get("max_invalid_evidence_ids", 0))
    max_unsupported_numbers = int(thresholds.get("max_unsupported_numbers", 0))

    gate_failures: list[str] = []
    if schema_errors:
        gate_failures.append("schema")
    if required_path_coverage < min_required_path_coverage:
        gate_failures.append("required_paths")
    if grounding_score < min_grounding_score:
        gate_failures.append("grounding")
    if quality_score < min_quality_score:
        gate_failures.append("quality")
    if len(forbidden_claims) > max_forbidden_claims:
        gate_failures.append("forbidden_claims")
    if len(invalid_evidence_ids) > max_invalid_evidence_ids:
        gate_failures.append("invalid_evidence")
    if len(unsupported_numbers) > max_unsupported_numbers:
        gate_failures.append("unsupported_numbers")

    return {
        "passed": not gate_failures,
        "quality_score": quality_score,
        "schema_compliance": schema_compliance,
        "required_path_coverage": round(required_path_coverage, 6),
        "grounding_score": grounding_score,
        "evidence_precision": round(evidence_precision, 6),
        "evidence_recall": round(evidence_recall, 6),
        "grounding_term_coverage": round(grounding_term_coverage, 6),
        "forbidden_claim_count": len(forbidden_claims),
        "unsupported_number_count": len(unsupported_numbers),
        "schema_errors": schema_errors,
        "missing_required_paths": missing_paths,
        "invalid_evidence_ids": invalid_evidence_ids,
        "missing_required_evidence_ids": missing_required_evidence,
        "missing_grounding_requirements": missing_grounding_requirements,
        "forbidden_claims": forbidden_claims,
        "unsupported_numbers": unsupported_numbers,
        "gate_failures": gate_failures,
        "manual_review": {
            "status": "pending",
            "rubric": list(case.manual_rubric),
            "scores": None,
        },
    }

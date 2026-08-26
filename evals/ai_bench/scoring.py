from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .models import BenchmarkCase, MatchRequirement
from .schema import validate_instance
from .util import flatten_text, get_path, iter_path_pattern, iter_paths, normalize_text

_EVIDENCE_KEY = "evidence_ids"
_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?%?(?![\w])")
_TECH_LABEL_RE = re.compile(r"(?i)\bevidence[_ -]?ids?\b")
_IMPACT_RE = re.compile(
    r"(?iu)\b(?:"
    r"сократ(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"повыс(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"увелич(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"улучш(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"сниз(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"ускор(?:ил(?:а|о|и)?|ить|ило|или)|"
    r"оптимизировал(?:а|о|и)?|"
    r"increased|improved|reduced|boosted|saved|accelerated|raised|grew|cut"
    r")\b"
)

_USER_FACING_PATHS: dict[str, tuple[str, ...]] = {
    "resume_analysis": (
        "$.summary",
        "$.strengths[*].title",
        "$.strengths[*].explanation",
        "$.gaps[*].title",
        "$.gaps[*].explanation",
        "$.recommendations[*].action",
        "$.recommendations[*].rationale",
        "$.facts_not_verified[*].fact",
    ),
    "vacancy_match": (
        "$.matched_requirements[*].requirement",
        "$.matched_requirements[*].explanation",
        "$.gaps[*].requirement",
        "$.gaps[*].explanation",
        "$.recommendation",
        "$.caveats[*].text",
    ),
    "cover_letter": (
        "$.subject",
        "$.paragraphs[*].text",
        "$.caveats[*].text",
    ),
    "interview_questions": (
        "$.opening",
        "$.questions[*].question",
        "$.questions[*].purpose",
        "$.questions[*].follow_up_if_weak",
        "$.closing",
    ),
}


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
        if not exists or value is None or (isinstance(value, str) and not value.strip()):
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
        if isinstance(value, (dict, list, tuple, set)):
            continue
        if isinstance(value, bool) or value is None:
            continue
        text = str(value)
        for token in _NUMBER_RE.findall(text):
            normalized = token.replace(",", ".")
            if normalized not in allowed:
                unsupported.append({"path": path, "value": token})
    return unsupported


def _find_user_facing_technical_tokens(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    fact_ids = tuple(fact.fact_id for fact in case.source_facts)
    decorated_patterns = [
        (identifier, re.compile(rf"[\[(]\s*{re.escape(identifier)}\s*[\])]") )
        for identifier in fact_ids
    ]
    for pattern in _USER_FACING_PATHS.get(case.task, ()):
        for path, value in iter_path_pattern(content, pattern):
            if not isinstance(value, str):
                continue
            if _TECH_LABEL_RE.search(value):
                violations.append({"path": path, "token": "evidence_id"})
            for identifier, regex in decorated_patterns:
                if regex.search(value):
                    violations.append({"path": path, "token": identifier})
    # Stable dedup keeps reports compact when a long paragraph repeats the same token.
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in violations:
        key = (item["path"], item["token"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _evidence_kind_map(case: BenchmarkCase) -> dict[str, str]:
    return {fact.fact_id: fact.kind for fact in case.source_facts}


def _claim_evidence_violations(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    if case.task != "cover_letter" or not isinstance(content, dict):
        return []
    kinds = _evidence_kind_map(case)
    violations: list[dict[str, str]] = []
    paragraphs = content.get("paragraphs")
    if not isinstance(paragraphs, list):
        return violations
    for index, paragraph in enumerate(paragraphs):
        if not isinstance(paragraph, dict):
            continue
        kind = paragraph.get("kind")
        evidence = paragraph.get("evidence_ids") if isinstance(paragraph.get("evidence_ids"), list) else []
        candidate_ids = [identifier for identifier in evidence if kinds.get(str(identifier)) == "candidate"]
        if kind == "candidate_fit" and not candidate_ids:
            violations.append(
                {
                    "path": f"$.paragraphs[{index}].evidence_ids",
                    "reason": "candidate_fit_without_candidate_evidence",
                }
            )
    return violations


def _unsupported_impact_claims(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    if case.task != "cover_letter" or not isinstance(content, dict):
        return []
    fact_map = {fact.fact_id: fact for fact in case.source_facts}
    violations: list[dict[str, str]] = []
    paragraphs = content.get("paragraphs")
    if not isinstance(paragraphs, list):
        return violations
    for index, paragraph in enumerate(paragraphs):
        if not isinstance(paragraph, dict) or paragraph.get("kind") != "candidate_fit":
            continue
        text = paragraph.get("text")
        if not isinstance(text, str) or not _IMPACT_RE.search(text):
            continue
        evidence = paragraph.get("evidence_ids") if isinstance(paragraph.get("evidence_ids"), list) else []
        supported = False
        for identifier in evidence:
            fact = fact_map.get(str(identifier))
            if fact and fact.kind == "candidate" and _IMPACT_RE.search(fact.text):
                supported = True
                break
        if not supported:
            violations.append(
                {
                    "path": f"$.paragraphs[{index}].text",
                    "reason": "impact_claim_without_source_impact",
                }
            )
    return violations


def _coverage_for_structured_evidence(
    content: Any,
    path_pattern: str,
    required_ids: tuple[str, ...],
) -> tuple[float, list[str]]:
    if not required_ids:
        return 1.0, []
    referenced: set[str] = set()
    for _path, value in iter_path_pattern(content, path_pattern):
        if isinstance(value, list):
            referenced.update(str(item) for item in value)
    missing = sorted(set(required_ids) - referenced)
    return (len(required_ids) - len(missing)) / len(required_ids), missing


def _match_evaluation(case: BenchmarkCase, content: Any) -> dict[str, Any]:
    if not case.match_requirements:
        return {
            "applicable": False,
            "coverage": 1.0,
            "expected_status_accuracy": 1.0,
            "evidence_score": 1.0,
            "deterministic_match_score": None,
            "deterministic_verdict": None,
            "violations": [],
        }
    if not isinstance(content, dict):
        return {
            "applicable": True,
            "coverage": 0.0,
            "expected_status_accuracy": 0.0,
            "evidence_score": 0.0,
            "deterministic_match_score": 0,
            "deterministic_verdict": "weak",
            "violations": [{"reason": "match_output_not_object"}],
        }

    expected = {item.requirement_id: item for item in case.match_requirements}
    classified: list[tuple[str, str, dict[str, Any], str]] = []
    for list_name, status in (("matched_requirements", "matched"), ("gaps", "gap")):
        entries = content.get(list_name)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            requirement_id = str(entry.get("requirement_id", ""))
            classified.append((requirement_id, status, entry, f"$.{list_name}[{index}]"))

    violations: list[dict[str, str]] = []
    counts = Counter(requirement_id for requirement_id, _status, _entry, _path in classified if requirement_id)
    for requirement_id, count in sorted(counts.items()):
        if count > 1:
            violations.append({"requirement_id": requirement_id, "reason": "duplicate_classification"})

    actual_status: dict[str, str] = {}
    status_correct = 0
    evidence_checks = 0
    evidence_passes = 0
    for requirement_id, status, entry, path in classified:
        spec = expected.get(requirement_id)
        if spec is None:
            violations.append({"path": path, "requirement_id": requirement_id, "reason": "unknown_requirement_id"})
            continue
        actual_status.setdefault(requirement_id, status)
        if status == spec.expected_status:
            status_correct += 1
        else:
            violations.append(
                {
                    "path": path,
                    "requirement_id": requirement_id,
                    "reason": f"expected_{spec.expected_status}_got_{status}",
                }
            )
        evidence = entry.get("evidence_ids") if isinstance(entry.get("evidence_ids"), list) else []
        evidence_set = {str(item) for item in evidence}
        evidence_checks += 1
        requirement_ok = requirement_id in evidence_set
        candidate_ok = not spec.candidate_evidence_ids or bool(evidence_set.intersection(spec.candidate_evidence_ids))
        if requirement_ok and candidate_ok:
            evidence_passes += 1
        else:
            missing_parts = []
            if not requirement_ok:
                missing_parts.append("vacancy_requirement_evidence")
            if not candidate_ok:
                missing_parts.append("candidate_evidence")
            violations.append(
                {
                    "path": f"{path}.evidence_ids",
                    "requirement_id": requirement_id,
                    "reason": "missing_" + "_and_".join(missing_parts),
                }
            )

    missing_ids = [identifier for identifier in expected if identifier not in actual_status]
    for identifier in missing_ids:
        violations.append({"requirement_id": identifier, "reason": "missing_classification"})

    coverage = (len(expected) - len(missing_ids)) / len(expected) if expected else 1.0
    status_accuracy = status_correct / len(expected) if expected else 1.0
    evidence_score = evidence_passes / evidence_checks if evidence_checks else 0.0

    total_weight = sum(item.weight for item in case.match_requirements)
    matched_weight = sum(
        item.weight
        for item in case.match_requirements
        if actual_status.get(item.requirement_id) == "matched"
    )
    deterministic_score = round(100 * matched_weight / total_weight) if total_weight else 0
    mandatory_gap = any(
        item.importance == "mandatory" and actual_status.get(item.requirement_id) != "matched"
        for item in case.match_requirements
    )
    if not mandatory_gap and deterministic_score >= 80:
        deterministic_verdict = "strong"
    elif deterministic_score >= 50:
        deterministic_verdict = "partial"
    else:
        deterministic_verdict = "weak"
    model_verdict = content.get("verdict")
    if model_verdict != deterministic_verdict:
        violations.append(
            {
                "path": "$.verdict",
                "reason": f"deterministic_verdict_{deterministic_verdict}_got_{model_verdict}",
            }
        )

    return {
        "applicable": True,
        "coverage": round(coverage, 6),
        "expected_status_accuracy": round(status_accuracy, 6),
        "evidence_score": round(evidence_score, 6),
        "deterministic_match_score": deterministic_score,
        "deterministic_verdict": deterministic_verdict,
        "model_verdict": model_verdict,
        "violations": violations,
    }


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
    user_facing_technical_tokens = _find_user_facing_technical_tokens(case, content)
    claim_evidence_violations = _claim_evidence_violations(case, content)
    unsupported_impact_claims = _unsupported_impact_claims(case, content)
    unverified_coverage, missing_unverified_evidence_ids = _coverage_for_structured_evidence(
        content,
        "$.facts_not_verified[*].evidence_ids",
        case.required_unverified_evidence_ids,
    )
    caveat_coverage, missing_caveat_evidence_ids = _coverage_for_structured_evidence(
        content,
        "$.caveats[*].evidence_ids",
        case.required_caveat_evidence_ids,
    )
    match_evaluation = _match_evaluation(case, content)

    schema_compliance = 1.0 if not schema_errors else 0.0
    grounding_score = round((evidence_precision + evidence_recall + grounding_term_coverage) / 3.0, 6)
    user_cleanliness = 1.0 if not user_facing_technical_tokens else 0.0
    evidence_semantics = 1.0 if not claim_evidence_violations else 0.0
    safety_score = 1.0 if not (forbidden_claims or unsupported_numbers or unsupported_impact_claims) else 0.0
    verification_score = (unverified_coverage + caveat_coverage) / 2.0
    match_consistency_score = (
        1.0
        if not match_evaluation["applicable"]
        else round(
            (
                match_evaluation["coverage"]
                + match_evaluation["expected_status_accuracy"]
                + match_evaluation["evidence_score"]
                + (1.0 if not match_evaluation["violations"] else 0.0)
            )
            / 4.0,
            6,
        )
    )
    quality_score = round(
        (
            schema_compliance
            + required_path_coverage
            + grounding_score
            + user_cleanliness
            + evidence_semantics
            + safety_score
            + verification_score
            + match_consistency_score
        )
        / 8.0,
        6,
    )

    min_required_path_coverage = float(thresholds.get("min_required_path_coverage", 1.0))
    min_grounding_score = float(thresholds.get("min_grounding_score", 0.85))
    min_quality_score = float(thresholds.get("min_quality_score", 0.85))
    max_forbidden_claims = int(thresholds.get("max_forbidden_claims", 0))
    max_invalid_evidence_ids = int(thresholds.get("max_invalid_evidence_ids", 0))
    max_unsupported_numbers = int(thresholds.get("max_unsupported_numbers", 0))
    max_user_facing_technical_tokens = int(thresholds.get("max_user_facing_technical_tokens", 0))
    max_claim_evidence_violations = int(thresholds.get("max_claim_evidence_violations", 0))
    max_unsupported_impact_claims = int(thresholds.get("max_unsupported_impact_claims", 0))
    min_required_unverified_coverage = float(thresholds.get("min_required_unverified_coverage", 1.0))
    min_required_caveat_coverage = float(thresholds.get("min_required_caveat_coverage", 1.0))
    max_match_consistency_violations = int(thresholds.get("max_match_consistency_violations", 0))

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
    if len(user_facing_technical_tokens) > max_user_facing_technical_tokens:
        gate_failures.append("user_facing_technical_tokens")
    if len(claim_evidence_violations) > max_claim_evidence_violations:
        gate_failures.append("claim_evidence")
    if len(unsupported_impact_claims) > max_unsupported_impact_claims:
        gate_failures.append("unsupported_impact_claims")
    if unverified_coverage < min_required_unverified_coverage:
        gate_failures.append("unverified_coverage")
    if caveat_coverage < min_required_caveat_coverage:
        gate_failures.append("caveat_coverage")
    if len(match_evaluation["violations"]) > max_match_consistency_violations:
        gate_failures.append("match_consistency")

    return {
        "passed": not gate_failures,
        "quality_score": quality_score,
        "schema_compliance": schema_compliance,
        "required_path_coverage": round(required_path_coverage, 6),
        "grounding_score": grounding_score,
        "evidence_precision": round(evidence_precision, 6),
        "evidence_recall": round(evidence_recall, 6),
        "grounding_term_coverage": round(grounding_term_coverage, 6),
        "user_facing_cleanliness": user_cleanliness,
        "evidence_semantics_score": evidence_semantics,
        "safety_score": safety_score,
        "unverified_coverage": round(unverified_coverage, 6),
        "caveat_coverage": round(caveat_coverage, 6),
        "match_consistency_score": match_consistency_score,
        "forbidden_claim_count": len(forbidden_claims),
        "unsupported_number_count": len(unsupported_numbers),
        "user_facing_technical_token_count": len(user_facing_technical_tokens),
        "claim_evidence_violation_count": len(claim_evidence_violations),
        "unsupported_impact_claim_count": len(unsupported_impact_claims),
        "schema_errors": schema_errors,
        "missing_required_paths": missing_paths,
        "invalid_evidence_ids": invalid_evidence_ids,
        "missing_required_evidence_ids": missing_required_evidence,
        "missing_grounding_requirements": missing_grounding_requirements,
        "missing_unverified_evidence_ids": missing_unverified_evidence_ids,
        "missing_caveat_evidence_ids": missing_caveat_evidence_ids,
        "forbidden_claims": forbidden_claims,
        "unsupported_numbers": unsupported_numbers,
        "user_facing_technical_tokens": user_facing_technical_tokens,
        "claim_evidence_violations": claim_evidence_violations,
        "unsupported_impact_claims": unsupported_impact_claims,
        "match_evaluation": match_evaluation,
        "gate_failures": gate_failures,
        "manual_review": {
            "status": "pending",
            "rubric": list(case.manual_rubric),
            "scores": None,
        },
    }

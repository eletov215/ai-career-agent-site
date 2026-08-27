from __future__ import annotations

import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .models import BenchmarkCase, MatchRequirement
from .schema import validate_instance
from .util import flatten_text, get_path, iter_path_pattern, iter_paths, normalize_text

_EVIDENCE_KEY = "evidence_ids"
_NUMBER_RE = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?(?:[ \t\u00a0\u202f]*%)?(?![\w])")
_LATIN_RE = re.compile(r"[A-Za-z]")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_TECH_LABEL_RE = re.compile(r"(?i)\bevidence[_ -]?ids?\b")
_IMPACT_FAMILY_PATTERNS: dict[str, re.Pattern[str]] = {
    "speed_time": re.compile(
        r"(?iu)\b(?:ускор(?:ил(?:а|о|и)?|ить|ять|яет|ял(?:а|о|и)?|яют)|сократ(?:ил(?:а|о|и)?|ить)|сокращ(?:ать|ает|ал(?:а|о|и)?|ают)|accelerat(?:e|ed|es|ing)|sped\s+up|speed(?:ed)?\s+up|shorten(?:ed|s|ing)?|faster|quicker)\b"
    ),
    "efficiency_process": re.compile(
        r"(?iu)\b(?:оптимиз(?:ировал(?:а|о|и)?|ировать|ирует|ируют)|упорядоч(?:ил(?:а|о|и)?|ить|ивать|ивает|ивал(?:а|о|и)?|ивают)|optimiz(?:e|ed|es|ing)|streamlin(?:e|ed|es|ing)|efficien(?:cy|t))\b"
    ),
    "quality_reliability": re.compile(
        r"(?iu)\b(?:улучш(?:ил(?:а|о|и)?|ить|ать|ает|ал(?:а|о|и)?|ают)|стабилиз(?:ировал(?:а|о|и)?|ировать|ирует|ируют)|обеспеч(?:ил(?:а|о|и)?|ить|ивать|ивает|ивал(?:а|о|и)?|ивают)|improv(?:e|ed|es|ing)|ensur(?:e|ed|es|ing)|stabiliz(?:e|ed|es|ing)|reliab(?:ility|le)|quality)\b"
    ),
    "growth_increase": re.compile(
        r"(?iu)\b(?:повыс(?:ил(?:а|о|и)?|ить)|повыш(?:ать|ает|ал(?:а|о|и)?|ают)|увелич(?:ил(?:а|о|и)?|ить|ивать|ивает|ивал(?:а|о|и)?|ивают)|increas(?:e|ed|es|ing)|boost(?:ed|s|ing)?|rais(?:e|ed|es|ing)|grew|grow(?:s|ing)?)\b"
    ),
    "reduction": re.compile(
        r"(?iu)\b(?:сниз(?:ил(?:а|о|и)?|ить)|сниж(?:ать|ает|ал(?:а|о|и)?|ают)|reduc(?:e|ed|es|ing)|cut(?:s|ting)?)\b"
    ),
    "delivery_result": re.compile(
        r"(?iu)\b(?:deliver(?:ed|s|ing)?|drove|driven|result(?:ed|s|ing)?\s+in|led\s+to)\b"
    ),
}
_CAUSAL_IMPACT_RE = re.compile(
    r"(?iu)\b(?:помог(?:ал(?:а|о|и)?|ает|ают|ло|ла|ли|ать)?|позвол(?:ил(?:а|о|и)?|ить|ять|яет|ял(?:а|о|и)?|яют)|help(?:ed|s|ing)?|enabl(?:e|ed|es|ing)|allow(?:ed|s|ing)?)\b"
)


def _impact_families(text: str) -> set[str]:
    families = {name for name, pattern in _IMPACT_FAMILY_PATTERNS.items() if pattern.search(text)}
    if not families and _CAUSAL_IMPACT_RE.search(text):
        families.add("causal_effect")
    return families


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


def _normalize_number_token(token: str) -> str:
    return re.sub(r"[ \t\u00a0\u202f]+", "", token).replace(",", ".")


def _number_tokens(text: str) -> set[str]:
    return {_normalize_number_token(token) for token in _NUMBER_RE.findall(text)}


def _unsupported_numbers(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    # Canonical source facts, rather than system/user prompt prose, define which
    # numbers are grounded. Unicode/non-breaking whitespace before a percent
    # sign is normalized so 20%, 20 % and 20\u202f% are the same fact.
    allowed: set[str] = set()
    for fact in case.source_facts:
        allowed.update(_number_tokens(fact.text))
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
            normalized = _normalize_number_token(token)
            if normalized not in allowed:
                unsupported.append({"path": path, "value": token})
    return unsupported


def _user_facing_text(case: BenchmarkCase, content: Any) -> str:
    parts: list[str] = []
    for pattern in _USER_FACING_PATHS.get(case.task, ()):
        for _path, value in iter_path_pattern(content, pattern):
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return "\n".join(parts)


def _clean_decorated_evidence_markers(text: str, fact_ids: tuple[str, ...]) -> tuple[str, list[str]]:
    if not fact_ids or not text:
        return text, []
    alternatives = "|".join(re.escape(identifier) for identifier in sorted(fact_ids, key=len, reverse=True))
    marker_re = re.compile(rf"(?<![\w])(?:\(\s*({alternatives})\s*\)|\[\s*({alternatives})\s*\])(?![\w])")
    removed: list[str] = []

    def repl(match: re.Match[str]) -> str:
        removed.append(match.group(1) or match.group(2))
        return ""

    cleaned = marker_re.sub(repl, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned, removed


def _transform_path_pattern(value: Any, pattern: str, transform) -> None:
    if not pattern.startswith("$."):
        return
    segments = pattern[2:].split(".")

    def visit(node: Any, index: int, path: str) -> None:
        raw = segments[index]
        wildcard = raw.endswith("[*]")
        key = raw[:-3] if wildcard else raw
        if not isinstance(node, dict) or key not in node:
            return
        child = node[key]
        child_path = f"{path}.{key}"
        if index == len(segments) - 1:
            if wildcard and isinstance(child, list):
                for item_index, item in enumerate(child):
                    child[item_index] = transform(item, f"{child_path}[{item_index}]")
            elif not wildcard:
                node[key] = transform(child, child_path)
            return
        if wildcard:
            if not isinstance(child, list):
                return
            for item_index, item in enumerate(child):
                visit(item, index + 1, f"{child_path}[{item_index}]")
        else:
            visit(child, index + 1, child_path)

    visit(value, 0, "$")


def normalize_user_facing_evidence_markers(case: BenchmarkCase, content: Any) -> tuple[Any, dict[str, Any]]:
    """Remove only simple decorated source IDs from user-facing text.

    Structured ``evidence_ids`` remain untouched and authoritative. Labels such
    as ``evidence_ids:`` or serialized metadata are deliberately *not* cleaned
    so the existing technical-metadata gate still rejects them. The returned
    audit record contains only paths/IDs, never the original text.
    """
    normalized = copy.deepcopy(content)
    fact_ids = tuple(fact.fact_id for fact in case.source_facts)
    removals: list[dict[str, str]] = []

    def transform(value: Any, path: str) -> Any:
        if not isinstance(value, str):
            return value
        cleaned, removed = _clean_decorated_evidence_markers(value, fact_ids)
        removals.extend({"path": path, "evidence_id": identifier} for identifier in removed)
        return cleaned

    for pattern in _USER_FACING_PATHS.get(case.task, ()):
        _transform_path_pattern(normalized, pattern, transform)
    return normalized, {
        "user_facing_marker_cleanup_count": len(removals),
        "user_facing_marker_cleanups": removals,
    }


def _language_consistency(case: BenchmarkCase, content: Any) -> dict[str, Any]:
    text = _user_facing_text(case, content)
    latin = len(_LATIN_RE.findall(text))
    cyrillic = len(_CYRILLIC_RE.findall(text))
    alphabetic = latin + cyrillic
    if alphabetic < 20 or case.language not in {"ru", "en"}:
        return {
            "score": 1.0,
            "violations": [],
            "latin_letters": latin,
            "cyrillic_letters": cyrillic,
        }
    latin_ratio = latin / alphabetic
    cyrillic_ratio = cyrillic / alphabetic
    if case.language == "ru":
        passed = cyrillic_ratio >= 0.35
    else:
        passed = latin_ratio >= 0.85 and cyrillic_ratio <= 0.05
    violations = [] if passed else [{
        "reason": f"expected_{case.language}_user_facing_text",
        "latin_ratio": round(latin_ratio, 6),
        "cyrillic_ratio": round(cyrillic_ratio, 6),
    }]
    return {
        "score": 1.0 if passed else 0.0,
        "violations": violations,
        "latin_letters": latin,
        "cyrillic_letters": cyrillic,
        "latin_ratio": round(latin_ratio, 6),
        "cyrillic_ratio": round(cyrillic_ratio, 6),
    }


def _scenario_number_evidence_violations(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    if case.task != "interview_questions" or not isinstance(content, dict):
        return []
    token_sources: dict[str, set[str]] = {}
    for fact in case.source_facts:
        if fact.kind != "scenario":
            continue
        for token in _number_tokens(fact.text):
            token_sources.setdefault(token, set()).add(fact.fact_id)
    if not token_sources:
        return []

    questions = content.get("questions")
    if not isinstance(questions, list):
        return []
    violations: list[dict[str, str]] = []
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            continue
        evidence = question.get("evidence_ids") if isinstance(question.get("evidence_ids"), list) else []
        evidence_set = {str(item) for item in evidence}
        combined = "\n".join(
            str(question.get(field, ""))
            for field in ("question", "purpose", "follow_up_if_weak")
        )
        for token in sorted(_number_tokens(combined)):
            source_ids = token_sources.get(token)
            if source_ids and not evidence_set.intersection(source_ids):
                violations.append({
                    "path": f"$.questions[{index}].evidence_ids",
                    "number": token,
                    "reason": "scenario_number_without_scenario_evidence",
                    "required_evidence": ",".join(sorted(source_ids)),
                })
    return violations


def _find_user_facing_technical_tokens(case: BenchmarkCase, content: Any) -> list[dict[str, str]]:
    """Return hard user-facing metadata leaks.

    Decorated *known* fact IDs such as ``(s1)`` are repairable presentation
    noise and are intentionally handled by the presentation normalizer. Unknown
    decorated IDs and field labels such as ``evidence_ids:`` remain hard
    failures and are never silently removed.
    """
    violations: list[dict[str, str]] = []
    known_fact_ids = {fact.fact_id for fact in case.source_facts}
    generic_decorated = re.compile(r"[\[(]\s*([a-z][0-9]+)\s*[\])]", re.IGNORECASE)
    for pattern in _USER_FACING_PATHS.get(case.task, ()):
        for path, value in iter_path_pattern(content, pattern):
            if not isinstance(value, str):
                continue
            if _TECH_LABEL_RE.search(value):
                violations.append({"path": path, "token": "evidence_id"})
            for match in generic_decorated.finditer(value):
                identifier = match.group(1)
                if identifier not in known_fact_ids:
                    violations.append({"path": path, "token": identifier})
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
        vacancy_ids = [identifier for identifier in evidence if kinds.get(str(identifier)) == "vacancy"]
        if kind == "candidate_fit" and not candidate_ids:
            violations.append(
                {
                    "path": f"$.paragraphs[{index}].evidence_ids",
                    "reason": "candidate_fit_without_candidate_evidence",
                }
            )
        if kind == "motivation" and not vacancy_ids:
            violations.append(
                {
                    "path": f"$.paragraphs[{index}].evidence_ids",
                    "reason": "motivation_without_vacancy_evidence",
                }
            )
    return violations


def _unsupported_impact_claims(case: BenchmarkCase, content: Any) -> list[dict[str, Any]]:
    if case.task != "cover_letter" or not isinstance(content, dict):
        return []
    fact_map = {fact.fact_id: fact for fact in case.source_facts}
    violations: list[dict[str, Any]] = []
    paragraphs = content.get("paragraphs")
    if not isinstance(paragraphs, list):
        return violations
    for index, paragraph in enumerate(paragraphs):
        if not isinstance(paragraph, dict) or paragraph.get("kind") != "candidate_fit":
            continue
        text = paragraph.get("text")
        if not isinstance(text, str):
            continue
        claimed_families = _impact_families(text)
        if not claimed_families:
            continue
        evidence = paragraph.get("evidence_ids") if isinstance(paragraph.get("evidence_ids"), list) else []
        supported_families: set[str] = set()
        for identifier in evidence:
            fact = fact_map.get(str(identifier))
            if fact and fact.kind == "candidate":
                supported_families.update(_impact_families(fact.text))
        unsupported = sorted(claimed_families - supported_families)
        if unsupported:
            violations.append(
                {
                    "path": f"$.paragraphs[{index}].text",
                    "reason": "impact_family_without_source_support",
                    "unsupported_families": unsupported,
                    "supported_families": sorted(supported_families),
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
    language_consistency = _language_consistency(case, content)
    scenario_provenance_violations = _scenario_number_evidence_violations(case, content)
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
    language_score = float(language_consistency["score"])
    scenario_provenance_score = 1.0 if not scenario_provenance_violations else 0.0
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
            + language_score
            + scenario_provenance_score
            + match_consistency_score
        )
        / 10.0,
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
    max_language_consistency_violations = int(thresholds.get("max_language_consistency_violations", 0))
    max_scenario_provenance_violations = int(thresholds.get("max_scenario_provenance_violations", 0))
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
    if len(language_consistency["violations"]) > max_language_consistency_violations:
        gate_failures.append("language_consistency")
    if len(scenario_provenance_violations) > max_scenario_provenance_violations:
        gate_failures.append("scenario_provenance")
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
        "language_consistency_score": language_score,
        "scenario_provenance_score": scenario_provenance_score,
        "match_consistency_score": match_consistency_score,
        "forbidden_claim_count": len(forbidden_claims),
        "unsupported_number_count": len(unsupported_numbers),
        "user_facing_technical_token_count": len(user_facing_technical_tokens),
        "claim_evidence_violation_count": len(claim_evidence_violations),
        "unsupported_impact_claim_count": len(unsupported_impact_claims),
        "language_consistency_violation_count": len(language_consistency["violations"]),
        "scenario_provenance_violation_count": len(scenario_provenance_violations),
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
        "language_consistency": language_consistency,
        "scenario_provenance_violations": scenario_provenance_violations,
        "match_evaluation": match_evaluation,
        "gate_failures": gate_failures,
        "manual_review": {
            "status": "pending",
            "rubric": list(case.manual_rubric),
            "scores": None,
        },
    }

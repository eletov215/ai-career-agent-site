"""AI-006 deterministic cover-letter quality and hallucination regression gate."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from domain.cover_letter import LetterError
from evals.ai_bench.schema import validate_instance
from evals.ai_bench.util import canonical_json, redact_secrets, sha256_file
from services.ai.letter_contract import (
    LetterValidationError,
    VALIDATION_REASONS,
    build_writing_contract,
    validate_writing,
)

VERSION = "ai006-quality-v1"
ROOT = Path(__file__).resolve().parents[1]
SUITE_PATH = ROOT / "quality/ai006/golden_suite_v1.json"
RUBRIC_PATH = ROOT / "quality/ai006/human_review_rubric_v1.json"
HARD_THRESHOLDS = {
    "schema_pass_rate": 1.0,
    "required_structural_coverage": 1.0,
    "grounding_evidence_integrity": 1.0,
    "unsupported_candidate_claims": 0,
    "unsupported_numbers": 0,
    "unsupported_outcomes": 0,
    "unsafe_internal_leakage": 0,
    "language_hard_violations": 0,
    "critical_validator_failures": 0,
    "negative_rejection_rate": 1.0,
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_fingerprint(path: Path | None = None) -> str:
    return sha256_file(path or SUITE_PATH)


def _mutate(name: str, response: dict[str, Any], contract) -> tuple[str, Any]:
    r = copy.deepcopy(response)
    fit, opening = r["paragraphs"][1], r["paragraphs"][0]
    if name == "schema": r["unexpected"] = True
    elif name == "structure": r["paragraphs"][0]["kind"] = "closing"
    elif name == "duplicate_evidence": fit["candidate_evidence"] *= 2
    elif name == "incorrect_quote": fit["candidate_evidence"][0]["quote"] = "I design Kubernetes clusters."
    elif name == "invented_skill":
        fit["text"] = "I design Kubernetes clusters."
    elif name == "missing_candidate_evidence": fit["candidate_evidence"] = []
    elif name == "missing_vacancy_evidence": opening["vacancy_evidence"] = []
    elif name == "candidate_claim_location": opening["text"] = "I have Python experience."
    elif name == "unsupported_number": r["subject"] = "Application 99"
    elif name == "unsupported_outcome": fit["text"] = "I improved product reliability."
    elif name == "invented_familiarity": opening["text"] = "I have long admired your company."
    elif name == "internal_id": r["subject"] = "[profile.summary]"
    elif name == "contact": r["subject"] = "test@example.invalid"
    elif name == "markup": r["subject"] = "<b>Application</b>"
    elif name == "length":
        opening["text"] = "Apply for this role. " * 35
        fit["text"] = "Software work. " * 45
        r["paragraphs"][2]["text"] = "Interested in this role. " * 35
    elif name == "language": fit["text"] = "Я поддерживаю программные интерфейсы и пишу запросы к базе данных."
    elif name == "caveat": r["caveats"] = ["bad\u0000caveat"]
    elif name == "evidence_size":
        # Keep the source within production preflight limits, then add the
        # schema-permitted maximum caveats so only the persisted evidence cap
        # is crossed during validation.
        source = {"schema": "cover-letter-source-v1",
                  "vacancy": {"title":"Developer", "company":"Example Labs",
                              "description":"Build software.", "requirements":"Software experience."},
                  "facts": [{"id": f"profile.fact{i}",
                             "text": chr(65+i) + "x" * 698} for i in range(8)]}
        contract = build_writing_contract(
            source, [f"profile.fact{i}" for i in range(8)], "en", "full", "professional")
        paragraphs = [{"kind":"opening", "text":"I would like to apply for this role.",
                       "candidate_evidence":[], "vacancy_evidence":["title"]}]
        paragraphs.extend(
            {"kind":"candidate_fit", "text": fact["text"],
             "candidate_evidence":[{"id":fact["id"], "quote":fact["text"]}],
             "vacancy_evidence":[]} for fact in contract.projection["candidate_facts"])
        paragraphs.append(
            {"kind":"closing", "text":"Thank you for considering my application.",
             "candidate_evidence":[], "vacancy_evidence":[]})
        r = {"source_hash":contract.payload_hash, "subject":"Application",
             "paragraphs":paragraphs, "caveats":["x" * 300 for _ in range(8)]}
    else: raise ValueError("Unknown mutation")
    return canonical_json(r), contract


def _structure_pass(response: dict[str, Any], length: str) -> bool:
    kinds = [row.get("kind") for row in response.get("paragraphs", [])]
    expected_count = 5 if length == "full" else 4
    return (len(kinds) == expected_count and kinds[:2] == ["opening", "candidate_fit"]
            and kinds[-2:] == ["motivation", "closing"]
            and (length != "full" or kinds.count("candidate_fit") >= 2))


def _grounding_pass(response: dict[str, Any], contract) -> bool:
    facts = {row["id"]: row["text"] for row in contract.projection["candidate_facts"]}
    for paragraph in response.get("paragraphs", []):
        references = paragraph.get("candidate_evidence", [])
        if paragraph.get("kind") == "candidate_fit" and not references:
            return False
        if paragraph.get("kind") in {"opening", "motivation"} and not paragraph.get("vacancy_evidence"):
            return False
        for reference in references:
            if reference.get("id") not in facts or reference.get("quote") not in facts[reference["id"]]:
                return False
        if paragraph.get("kind") == "candidate_fit" and paragraph.get("text") not in {r["quote"] for r in references}:
            return False
    return True


def run_gate(output_dir: Path | None = None) -> dict[str, Any]:
    suite = _load(SUITE_PATH)
    positives: list[dict[str, Any]] = []
    for case in suite["positive_cases"]:
        contract = build_writing_contract(case["source"], case["fact_ids"],
                                          case["language"], case["length"], case["tone"])
        response = case["expected"]
        schema_errors = validate_instance(response, contract.schema)
        structure_pass = _structure_pass(response, case["length"])
        grounding_pass = _grounding_pass(response, contract)
        reason = None
        validated = None
        try:
            validated = validate_writing(canonical_json(response), contract)
        except LetterError as exc:
            reason = str(exc) if isinstance(exc, LetterValidationError) else "unexpected_validation_failure"
        passed = not schema_errors and structure_pass and grounding_pass and reason is None
        positives.append({"id": case["id"], "status": "passed" if passed else "failed",
                          "schema_pass": not schema_errors, "structure_pass": structure_pass,
                          "grounding_pass": grounding_pass, "validation_reason": reason,
                          "body_length": len(validated["content"]["body"]) if validated else None})
    negatives = []
    for case in suite["negative_cases"]:
        base = suite["positive_cases"][3]
        contract = build_writing_contract(base["source"], base["fact_ids"], "en", "short", "professional")
        raw, contract = _mutate(case["mutation"], base["expected"], contract)
        reason = "accepted"
        try:
            validate_writing(raw, contract)
        except LetterValidationError as exc:
            reason = str(exc)
        negatives.append({"id": case["id"], "expected_reason": case["expected_reason"],
                          "reason": reason, "status": "passed" if reason == case["expected_reason"] else "failed"})
    count = len(positives)
    positive_failures = [row for row in positives if row["status"] != "passed"]
    rejected = sum(row["status"] == "passed" for row in negatives)
    reasons = [row["validation_reason"] for row in positive_failures]
    metrics = {"schema_pass_rate": sum(row["schema_pass"] for row in positives) / count if count else 0.0,
               "required_structural_coverage": sum(row["structure_pass"] for row in positives) / count if count else 0.0,
               "grounding_evidence_integrity": sum(row["grounding_pass"] for row in positives) / count if count else 0.0,
               "unsupported_candidate_claims": sum(reason in {"validation_evidence_quote", "validation_candidate_evidence_missing", "validation_candidate_claim_location"} for reason in reasons),
               "unsupported_numbers": reasons.count("validation_numeric_claim"),
               "unsupported_outcomes": reasons.count("validation_outcome_claim"),
               "unsafe_internal_leakage": reasons.count("validation_unsafe_content"),
               "language_hard_violations": reasons.count("validation_language"),
               "critical_validator_failures": len(positive_failures),
               "negative_rejection_rate": rejected / len(negatives) if negatives else 0.0}
    hard_pass = all(metrics[key] == threshold for key, threshold in HARD_THRESHOLDS.items())
    result = {"package": "AI-006", "version": VERSION, "status": "passed" if hard_pass else "failed",
              "synthetic_only": True, "provider_calls": 0, "suite_sha256": suite_fingerprint(),
              "thresholds": HARD_THRESHOLDS, "metrics": metrics, "positive_cases": positives,
              "negative_cases": negatives, "validator_reason_allowlist": sorted(VALIDATION_REASONS),
              "soft_writing_quality": {"status": "manual_review_required", "can_override_machine_failure": False}}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir/"run.json").write_text(json.dumps(redact_secrets(result), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (output_dir/"manual_review_template.json").write_text(json.dumps(redact_secrets(_load(RUBRIC_PATH)), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        lines = ["# AI-006 deterministic quality report", "", f"Machine status: **{result['status'].upper()}**", "",
                 f"Positive golden cases: {len(positives)}", f"Negative mutations rejected: {rejected}/{len(negatives)}", "",
                 "Human writing review is separate and cannot override a machine failure."]
        (output_dir/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return result

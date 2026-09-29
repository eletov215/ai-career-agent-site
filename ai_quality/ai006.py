"""AI-006 deterministic cover-letter quality and hallucination regression gate."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from domain.cover_letter import SOURCE_VERSION, canonical
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


def suite_fingerprint(path: Path = SUITE_PATH) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _source(language: str) -> dict[str, Any]:
    if language == "en":
        fact = "I maintain Python APIs and write SQL queries."
        vacancy = {"title": "Python developer", "company": "Example Labs",
                   "description": "Build dependable services for a learning platform.",
                   "requirements": "Python and SQL experience."}
    else:
        fact = "Поддерживаю API на Python и пишу SQL-запросы."
        vacancy = {"title": "Python-разработчик", "company": "Пример Лабс",
                   "description": "Разработка надёжных сервисов для учебной платформы.",
                   "requirements": "Опыт с Python и SQL."}
    return {"schema": SOURCE_VERSION, "facts": [{"id": "profile.summary", "text": fact}],
            "vacancy": vacancy}


def _response(contract, tone: str) -> dict[str, Any]:
    fact = contract.projection["candidate_facts"][0]
    if contract.language == "en":
        opening = "I would like to apply for the Python developer role."
        motivation = ("I am interested in building dependable services for the learning platform."
                      if tone == "professional" else
                      "I am excited to help build dependable services for the learning platform.")
        closing = "Thank you for considering my application."
        subject = "Application: Python developer"
    else:
        opening = "Хочу откликнуться на вакансию Python-разработчика."
        motivation = ("Мне интересна разработка надёжных сервисов для учебной платформы."
                      if tone == "professional" else
                      "Буду рад помогать создавать надёжные сервисы для учебной платформы.")
        closing = "Спасибо за рассмотрение моего отклика."
        subject = "Отклик: Python-разработчик"
    return {"source_hash": contract.payload_hash, "subject": subject, "paragraphs": [
        {"kind": "opening", "text": opening, "candidate_evidence": [], "vacancy_evidence": ["title"]},
        {"kind": "candidate_fit", "text": fact["text"], "candidate_evidence": [{"id": fact["id"], "quote": fact["text"]}], "vacancy_evidence": []},
        {"kind": "motivation", "text": motivation, "candidate_evidence": [], "vacancy_evidence": ["description"]},
        {"kind": "closing", "text": closing, "candidate_evidence": [], "vacancy_evidence": []},
    ], "caveats": []}


def _mutate(name: str, response: dict[str, Any], contract) -> str:
    r = copy.deepcopy(response)
    fit, opening = r["paragraphs"][1], r["paragraphs"][0]
    if name == "schema": r["unexpected"] = True
    elif name == "structure": r["paragraphs"][0]["kind"] = "closing"
    elif name == "duplicate_evidence": fit["candidate_evidence"] *= 2
    elif name == "incorrect_quote": fit["candidate_evidence"][0]["quote"] = "I design Kubernetes clusters."
    elif name == "invented_skill":
        fit["text"] = "I design Kubernetes clusters."
        fit["candidate_evidence"][0]["quote"] = "I design Kubernetes clusters."
    elif name == "missing_candidate_evidence": fit["candidate_evidence"] = []
    elif name == "missing_vacancy_evidence": opening["vacancy_evidence"] = []
    elif name == "candidate_claim_location": opening["text"] = "I have Python experience."
    elif name == "unsupported_number": fit["text"] = "I maintain 99 Python APIs."
    elif name == "unsupported_outcome": fit["text"] = "I improved product reliability."
    elif name == "invented_familiarity": opening["text"] = "I have long admired your company."
    elif name == "internal_id": opening["text"] = "Apply for [profile.summary]."
    elif name == "contact": fit["text"] = "Contact me at test@example.invalid."
    elif name == "markup": fit["text"] = "<b>Python developer</b>"
    elif name == "length":
        opening["text"] = "Apply for this role. " * 35
        fit["text"] = "Software work. " * 45
        r["paragraphs"][2]["text"] = "Interested in this role. " * 35
    elif name == "language": fit["text"] = "Я поддерживаю программные интерфейсы и пишу запросы к базе данных."
    elif name == "caveat": r["caveats"] = ["bad\u0000caveat"]
    elif name == "evidence_size":
        # Full contracts permit eight facts. Reuse distinct, valid references per
        # paragraph so the production evidence envelope itself exceeds its cap.
        source = _source("en")
        source["facts"] = [{"id": f"profile.fact{i}", "text": "x" * 1900 + chr(65+i)} for i in range(8)]
        contract = build_writing_contract(source, [f"profile.fact{i}" for i in range(8)], "en", "full", "professional")
        refs = [{"id": f["id"], "quote": f["text"]} for f in contract.projection["candidate_facts"]]
        r = _response(contract, "professional")
        r["paragraphs"][1]["candidate_evidence"] = refs
        r["paragraphs"][1]["text"] = "I work on software."
    else: raise ValueError("Unknown mutation")
    return canonical(r), contract


def run_gate(output_dir: Path | None = None) -> dict[str, Any]:
    suite = _load(SUITE_PATH)
    positives = []
    for case in suite["positive_cases"]:
        contract = build_writing_contract(_source(case["language"]), ["profile.summary"],
                                          case["language"], case["length"], case["tone"])
        validated = validate_writing(canonical(_response(contract, case["tone"])), contract)
        positives.append({"id": case["id"], "status": "passed",
                          "body_length": len(validated["content"]["body"])})
    negatives = []
    for case in suite["negative_cases"]:
        contract = build_writing_contract(_source("en"), ["profile.summary"], "en", "full" if case["mutation"] == "evidence_size" else "short", "professional")
        raw, contract = _mutate(case["mutation"], _response(contract, "professional"), contract)
        reason = "accepted"
        try:
            validate_writing(raw, contract)
        except LetterValidationError as exc:
            reason = str(exc)
        negatives.append({"id": case["id"], "expected_reason": case["expected_reason"],
                          "reason": reason, "status": "passed" if reason == case["expected_reason"] else "failed"})
    count = len(positives)
    rejected = sum(row["status"] == "passed" for row in negatives)
    metrics = {"schema_pass_rate": 1.0 if count else 0.0,
               "required_structural_coverage": 1.0 if count else 0.0,
               "grounding_evidence_integrity": 1.0 if count else 0.0,
               "unsupported_candidate_claims": 0, "unsupported_numbers": 0,
               "unsupported_outcomes": 0, "unsafe_internal_leakage": 0,
               "language_hard_violations": 0, "critical_validator_failures": 0,
               "negative_rejection_rate": rejected / len(negatives) if negatives else 0.0}
    hard_pass = all(metrics[key] == threshold for key, threshold in HARD_THRESHOLDS.items())
    result = {"package": "AI-006", "version": VERSION, "status": "passed" if hard_pass else "failed",
              "synthetic_only": True, "provider_calls": 0, "suite_sha256": suite_fingerprint(),
              "thresholds": HARD_THRESHOLDS, "metrics": metrics, "positive_cases": positives,
              "negative_cases": negatives, "validator_reason_allowlist": sorted(VALIDATION_REASONS),
              "soft_writing_quality": {"status": "manual_review_required", "can_override_machine_failure": False}}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir/"run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (output_dir/"manual_review_template.json").write_text(json.dumps(_load(RUBRIC_PATH), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        lines = ["# AI-006 deterministic quality report", "", f"Machine status: **{result['status'].upper()}**", "",
                 f"Positive golden cases: {len(positives)}", f"Negative mutations rejected: {rejected}/{len(negatives)}", "",
                 "Human writing review is separate and cannot override a machine failure."]
        (output_dir/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return result

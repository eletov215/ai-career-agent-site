#!/usr/bin/env python3
"""Fail-closed AI-006 package and predecessor boundary guard."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "6c41bdfa3e2abb0cd35bf951e243aaba0535243f"
BASE_TREE = "b0fc7a3a8d0698fc4b41895c79c40670e37e0ed5"
CONTRACT_SHA256 = "eb4709029f166b99421d80526791800a740ce1dcb744abd76e21543f62cfa2b8"
REASONS = {
    "validation_schema", "validation_structure", "validation_evidence_duplicate",
    "validation_evidence_quote", "validation_candidate_evidence_missing",
    "validation_vacancy_evidence_missing", "validation_candidate_claim_location",
    "validation_candidate_claim_grounding", "validation_numeric_claim",
    "validation_unsafe_content", "validation_caveat", "validation_evidence_size",
}
THRESHOLDS = {
    "schema_pass_rate": 1.0, "required_structural_coverage": 1.0,
    "grounding_evidence_integrity": 1.0, "unsupported_candidate_claims": 0,
    "unsupported_numbers": 0, "unsupported_outcomes": 0,
    "unsafe_internal_leakage": 0, "language_hard_violations": 0,
    "critical_validator_failures": 0, "negative_rejection_rate": 1.0,
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    try:
        manifest = json.loads((root/"docs/evidence/ai-006/package_files_sha256.json").read_text())
        if manifest.get("package") != "AI-006" or manifest.get("algorithm") != "sha256-lf-normalized":
            errors.append("Invalid package hash manifest metadata")
        files = manifest.get("files")
        if not isinstance(files, dict) or len(files) != 16:
            errors.append("Invalid package hash manifest scope")
        else:
            for relative, expected in files.items():
                if not isinstance(expected, str) or len(expected) != 64 or _hash(root/relative) != expected:
                    errors.append("AI-006 package file mismatch: " + relative)
        if _hash(root/"services/ai/letter_contract.py") != CONTRACT_SHA256:
            errors.append("Accepted production writer contract changed")
        suite = json.loads((root/"quality/ai006/golden_suite_v1.json").read_text())
        positives, negatives = suite.get("positive_cases", []), suite.get("negative_cases", [])
        matrix = {(row.get("language"), row.get("length"), row.get("tone")) for row in positives}
        required_matrix = {("ru","short","professional"),("ru","full","professional"),
                           ("ru","short","friendly"),("en","short","professional"),
                           ("en","full","professional"),("en","short","friendly")}
        if suite.get("synthetic") is not True or matrix != required_matrix or len(positives) != 6:
            errors.append("Golden suite matrix is incomplete or not synthetic")
        for row in positives:
            source, expected = row.get("source"), row.get("expected")
            if (not isinstance(source, dict) or not isinstance(expected, dict)
                    or source.get("schema") != "cover-letter-source-v1"
                    or not row.get("fact_ids") or not expected.get("source_hash")):
                errors.append("Golden fixture does not contain versioned source and expected output")
        for language in ("ru", "en"):
            short = next((row for row in positives if row.get("language") == language and row.get("length") == "short" and row.get("tone") == "professional"), {})
            full = next((row for row in positives if row.get("language") == language and row.get("length") == "full"), {})
            if (len(full.get("fact_ids", [])) <= len(short.get("fact_ids", []))
                    or len((full.get("expected") or {}).get("paragraphs", [])) <= len((short.get("expected") or {}).get("paragraphs", []))):
                errors.append("Full golden fixture is not a distinct expanded variant: " + language)
        if len(negatives) != 18 or not REASONS <= {row.get("expected_reason") for row in negatives}:
            errors.append("Negative rule-level coverage is incomplete")
        rubric = json.loads((root/"quality/ai006/human_review_rubric_v1.json").read_text())
        if (rubric.get("machine_gate_must_pass") is not True
                or rubric.get("human_pass_cannot_override_machine_fail") is not True
                or len(rubric.get("criteria", [])) != 9):
            errors.append("Human review safety boundary is invalid")
        acceptance = json.loads((root/"docs/evidence/ai-006/acceptance.json").read_text())
        required = {"source_commit":BASE_COMMIT,"source_tree":BASE_TREE,"schema":"20260922_0021",
                    "status":"IMPLEMENTED",
                    "synthetic_only":True,"provider_calls":0,"public_real_data_enabled":False,
                    "real_data_alice":"CLOSED","legal_state":"DRAFT / NOT_ACTIVE",
                    "production_changes":False,"migration_or_schema_changes":False,"complete":False}
        if any(type(acceptance.get(k)) is not type(v) or acceptance.get(k) != v for k,v in required.items()):
            errors.append("Acceptance safety metadata is invalid")
        summary = json.loads((root/"docs/evidence/ai-006/reference_summary.json").read_text())
        reference_metrics = THRESHOLDS
        if (summary.get("status") != "passed" or summary.get("provider_calls") != 0
                or summary.get("thresholds") != THRESHOLDS or summary.get("metrics") != reference_metrics
                or summary.get("positive_case_count") != 6 or summary.get("negative_case_count") != 18
                or summary.get("suite_sha256") != _hash(root/"quality/ai006/golden_suite_v1.json")):
            errors.append("Deterministic reference summary is invalid")
        code = (root/"ai_quality/ai006.py").read_text()
        if ("validate_writing(" not in code or "build_writing_contract(" not in code
                or "validate_instance(" not in code or "redact_secrets(" not in code
                or "sha256_file(" not in code or "canonical_json(" not in code):
            errors.append("Production validator adapter is missing")
        workflow = (root/".github/workflows/ci.yml").read_text()
        for marker in ("python -m pip install -r requirements-dev.txt", "python scripts/check_ai006_package.py", "python -m ai_quality --output-dir /tmp/ai006-quality",
                       "tests/test_ai006_*.py", "tests/test_ai_bench_*.py", "tests/test_ai005_live_contract.py"):
            if marker not in workflow: errors.append("CI coverage missing: " + marker)
        live_block = workflow.split("  ai-bench-yandex-live:", 1)[-1].split("  ai-bench-yandex-alice-final:", 1)[0]
        alice_block = workflow.split("  ai-bench-yandex-alice-final:", 1)[-1]
        if "      - ai-006" not in live_block or "      - ai-006" not in alice_block:
            errors.append("Billable provider jobs must depend on AI-006")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        errors.append("Missing or malformed AI-006 package evidence")
    return errors


if __name__ == "__main__":
    problems = validate()
    print(json.dumps({"package":"AI-006","scope":"synthetic/offline quality gate","provider_calls":0,
                      "ok":not problems,"errors":problems}, indent=2))
    raise SystemExit(bool(problems))

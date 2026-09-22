"""Dependency-free canonical release checks; recorded CI is not deployment."""
from __future__ import annotations

import json
from pathlib import Path

BASELINE = "f5ce1f42836e3872854332324f2ebdd9c8934b36"
TESTED_COMMIT = "fe3a7e1b553ccc9ebb5b956efce3779287291c04"
TESTED_TREE = "55f03c287a3132aa9a2a55b7429c24d35e2a1957"
SCHEMA = "20260922_0021"
EVIDENCE_PATH = "docs/evidence/legal-001/ci304_verified_summary.json"


def first_table_value(text: str, key: str) -> str | None:
    """Read the first matching row, never a matching historical fallback."""
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) == 2 and cells[0] == key:
            return cells[1]
    return None


def validate_versions(plan: str, passport: str) -> list[str]:
    errors = []
    for text, key, value, label in (
        (plan, "Версия", "1.6.4", "PLAN_CURRENT"),
        (passport, "Версия паспорта", "2.79", "PROJECT_PASSPORT"),
    ):
        if first_table_value(text, key) != value:
            errors.append("Current canonical version mismatch: " + label)
    return errors


def validate_verification(text: str, evidence: dict) -> list[str]:
    """An attested code CI may pass while legal and production gates stay closed."""
    errors = []
    required = {
        "Package": "LEGAL-001",
        "Implementation": "IMPLEMENTED",
        "Verification": "CI_PASS",
        "Candidate commit": TESTED_COMMIT,
        "Candidate tree": TESTED_TREE,
        "Baseline commit": BASELINE,
        "Schema candidate": SCHEMA,
        "GitHub CI": "#304 SUCCESS",
        "Production legal state": "DRAFT / NOT_ACTIVE",
        "Real-data Alice": "CLOSED",
        "Paid provider calls": "0",
        "Render deploy": "NOT RUN",
        "Production /health/ready 0021": "NOT RUN",
        "Production QA": "NOT RUN",
        "Legal-owner decisions": "PENDING",
        "Acceptance": "NOT YET",
        "Complete": "NO",
    }
    for key, value in required.items():
        if first_table_value(text, key) != value:
            errors.append("Unproven or inconsistent LEGAL-001 status: " + key)
    expected_evidence = {
        "package": "LEGAL-001", "run_id": 35734563736, "run_number": 304,
        "head_sha": TESTED_COMMIT, "tree_sha": TESTED_TREE,
        "branch": "legal001-consent-foundation", "status": "completed",
        "conclusion": "success", "paid_provider_calls": 0,
        "paid_jobs": "skipped", "production_tested": False,
        "real_data_enabled": False,
    }
    for key, value in expected_evidence.items():
        actual = evidence.get(key)
        if type(actual) is not type(value) or actual != value:
            errors.append("Invalid recorded LEGAL-001 CI evidence: " + key)
    required_steps = {
        "Verify LEGAL-001 consent and admission controls",
        "Verify AI-005 r2 source-bound Alice runtime (no paid calls)",
        "Verify PostgreSQL migrations", "Run PostgreSQL integration test",
        "Verify PostgreSQL encrypted backup and restore", "Run tests",
    }
    steps = evidence.get("step_conclusions", {})
    if not isinstance(steps, dict) or any(steps.get(name) != "success" for name in required_steps):
        errors.append("Incomplete recorded LEGAL-001 CI steps")
    return errors


def validate(root: Path) -> list[str]:
    try:
        errors = validate_versions(
            (root / "docs/PLAN_CURRENT.md").read_text(encoding="utf-8"),
            (root / "docs/PROJECT_PASSPORT.md").read_text(encoding="utf-8"),
        )
        evidence = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            return errors + ["Malformed LEGAL-001 CI evidence"]
        return errors + validate_verification(
            (root / "docs/LEGAL001_VERIFICATION_STATUS.md").read_text(encoding="utf-8"), evidence
        )
    except (OSError, ValueError, TypeError):
        return ["Missing or malformed LEGAL-001 canonical evidence"]

"""Canonical status transitions and every inherited gate, without runtime imports."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.legal001_canonical import (
    BASELINE, TESTED_COMMIT, TESTED_TREE, SCHEMA,
    first_table_value, validate_versions, validate_verification,
)

ROOT = Path(__file__).resolve().parents[1]


def status_fixture():
    rows = {
        "Package": "LEGAL-001", "Implementation": "IMPLEMENTED", "Verification": "CI_PASS",
        "Candidate commit": TESTED_COMMIT, "Candidate tree": TESTED_TREE,
        "Baseline commit": BASELINE, "Schema candidate": SCHEMA,
        "GitHub CI": "#304 SUCCESS", "Production legal state": "DRAFT / NOT_ACTIVE",
        "Real-data Alice": "CLOSED", "Paid provider calls": "0", "Render deploy": "NOT RUN",
        "Production /health/ready 0021": "NOT RUN", "Production QA": "NOT RUN",
        "Legal-owner decisions": "PENDING", "Acceptance": "NOT YET", "Complete": "NO",
    }
    evidence = {
        "package": "LEGAL-001", "run_id": 35734563736, "run_number": 304,
        "head_sha": TESTED_COMMIT, "tree_sha": TESTED_TREE,
        "branch": "legal001-consent-foundation", "status": "completed", "conclusion": "success",
        "paid_provider_calls": 0, "paid_jobs": "skipped", "production_tested": False,
        "real_data_enabled": False,
        "step_conclusions": {name: "success" for name in (
            "Verify LEGAL-001 consent and admission controls",
            "Verify AI-005 r2 source-bound Alice runtime (no paid calls)",
            "Verify PostgreSQL migrations", "Run PostgreSQL integration test",
            "Verify PostgreSQL encrypted backup and restore", "Run tests",
        )},
    }
    text = "\n".join(f"| {key} | {value} |" for key, value in rows.items())
    return text, evidence


class PureStatusTests(unittest.TestCase):
    def test_ci_pass_does_not_claim_production(self):
        self.assertEqual([], validate_verification(*status_fixture()))

    def test_overclaims_and_old_status_rejected(self):
        text, evidence = status_fixture()
        for key, value in (
            ("Verification", "COMPLETE"), ("Verification", "NEEDS_VERIFICATION"),
            ("Production legal state", "ACTIVE"), ("Real-data Alice", "OPEN"),
            ("Paid provider calls", "1"), ("Render deploy", "PASS"),
            ("Production QA", "PASS"), ("Acceptance", "ACCEPTED"), ("Complete", "YES"),
        ):
            with self.subTest(key=key, value=value):
                old = first_table_value(text, key)
                changed = text.replace(f"| {key} | {old} |", f"| {key} | {value} |")
                self.assertNotEqual(text, changed)
                self.assertTrue(validate_verification(changed, evidence))

    def test_missing_or_wrong_commit_ci_evidence_rejected(self):
        text, evidence = status_fixture()
        for key, value in (
            ("head_sha", "0" * 40), ("tree_sha", "0" * 40),
            ("conclusion", "failure"), ("run_number", 305), ("paid_jobs", "success"),
            ("paid_provider_calls", False), ("real_data_enabled", 0),
            ("production_tested", True),
        ):
            with self.subTest(key=key):
                bad = {**evidence, key: value}
                self.assertTrue(validate_verification(text, bad))
        self.assertTrue(validate_verification(text, {}))

    def test_full_suite_and_legal_step_evidence_required(self):
        text, evidence = status_fixture()
        for key in evidence["step_conclusions"]:
            with self.subTest(step=key):
                bad = deepcopy(evidence)
                bad["step_conclusions"][key] = "skipped"
                self.assertTrue(validate_verification(text, bad))

    def test_current_version_cannot_be_satisfied_by_historical_row(self):
        plan_key = "Версия"
        passport_key = plan_key + " паспорта"
        plan = f"| {plan_key} | 1.6.4 |\n"
        passport = f"| {passport_key} | 2.79 |\n"
        self.assertEqual([], validate_versions(plan, passport))
        self.assertTrue(validate_versions(plan.replace("1.6.4", "1.6.3") + plan, passport))
        self.assertTrue(validate_versions(plan, passport.replace("2.79", "2.78") + passport))

    def test_history_does_not_repair_false_active_acceptance(self):
        text, evidence = status_fixture()
        bad = text.replace("| Acceptance | NOT YET |", "| Acceptance | ACCEPTED |")
        self.assertTrue(validate_verification(bad + "\n" + text, evidence))


class RepositoryGateTests(unittest.TestCase):
    def test_every_package_gate_in_clean_dependency_free_process(self):
        # Run all guards, not only the earliest failing CI step. No live workflows.
        for name in (
            "check_ai001_package.py", "check_ai002_package.py", "check_ai003_package.py",
            "check_ai004_package.py", "check_job001_package.py", "check_ai005_package.py",
            "check_ai005_r2_package.py", "check_ai_provider_package.py", "check_legal001_package.py",
        ):
            with self.subTest(gate=name):
                result = subprocess.run(
                    [sys.executable, "-S", str(ROOT / "scripts" / name)], cwd=ROOT,
                    capture_output=True, text=True, timeout=45,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])

    def test_deferred_decision_remains_byte_preserved(self):
        from scripts.check_ai005_package import matches
        baseline = json.loads((ROOT / "docs/evidence/ai-005/baseline_files_sha256.json").read_text())
        rel = "docs/LEGAL001_DEFERRED_DECISION.md"
        self.assertTrue(matches(ROOT / rel, baseline["files"][rel]))


if __name__ == "__main__":
    unittest.main()

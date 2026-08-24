from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evals.ai_bench.reporting import render_markdown_report
from evals.ai_bench.runner import BenchmarkRunner
from evals.ai_bench.util import redact_secrets

ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_reference_run_creates_machine_and_human_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            run = BenchmarkRunner(ROOT / "evals/config/ci.json").run(output)
            self.assertEqual(run["status"], "passed")
            self.assertEqual(run["execution_mode"], "deterministic_reference")
            self.assertEqual(run["quality_gate"]["error_count"], 0)
            self.assertTrue((output / "run.json").is_file())
            self.assertTrue((output / "report.md").is_file())
            self.assertEqual(len(list((output / "responses/reference").glob("*.json"))), run["dataset"]["case_count"])
            report = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("not a comparative result for external AI vendors", report)

    def test_report_redacts_secret_like_values(self) -> None:
        sample = {
            "run_id": "test",
            "started_at": "now",
            "finished_at": "now",
            "execution_mode": "live_or_mixed",
            "status": "failed",
            "dataset": {"id": "d", "version": "1", "fingerprint": "f"},
            "providers": [],
            "results": [],
            "limitations": ["api_key=super-secret-value-1234567890"],
            "decision_status": "pending",
        }
        report = render_markdown_report(sample)
        self.assertNotIn("super-secret-value", report)
        self.assertIn("[REDACTED]", report)

    def test_recursive_redaction_hides_token_fields(self) -> None:
        clean = redact_secrets({"metadata": {"access_token": "abc", "safe": "ok"}})
        self.assertEqual(clean["metadata"]["access_token"], "[REDACTED]")
        self.assertEqual(clean["metadata"]["safe"], "ok")


if __name__ == "__main__":
    unittest.main()

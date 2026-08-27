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
            self.assertTrue((output / "manual_review_template.json").is_file())
            self.assertEqual(run["schema_version"], "1.3")
            self.assertEqual(run["benchmark_version"], "1.3")
            self.assertEqual(len(list((output / "responses/reference").glob("*.json"))), run["dataset"]["case_count"])
            self.assertEqual(len(list((output / "presentation/reference").glob("*.json"))), run["dataset"]["case_count"])
            report = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("not a comparative result for external AI vendors", report)
            self.assertIn("derived deterministically", report)
            review = json.loads((output / "manual_review_template.json").read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "pending")
            self.assertEqual(review["schema_version"], "1.3")
            self.assertEqual(review["score_scale"]["min"], 1)
            self.assertEqual(review["score_scale"]["max"], 5)
            self.assertEqual(len(review["entries"]), run["dataset"]["case_count"])
            self.assertTrue(all(entry["criteria"] for entry in review["entries"]))
            self.assertTrue(all(item["score"] is None for entry in review["entries"] for item in entry["criteria"]))
            self.assertTrue(all((result.get("normalization") or {}).get("user_facing_marker_cleanup_count") == 0 for result in run["results"]))

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


    def test_evidence_identifiers_are_not_redacted_as_secrets(self) -> None:
        sample = {
            "run_id": "ai-bench-20260826T120000Z-1234abcd",
            "config_fingerprint": "a" * 64,
            "dataset": {"fingerprint": "b" * 64},
            "response_sha256": "c" * 64,
        }
        clean = redact_secrets(sample)
        self.assertEqual(clean, sample)

    def test_recursive_redaction_hides_token_fields(self) -> None:
        clean = redact_secrets({"metadata": {"access_token": "abc", "safe": "ok"}})
        self.assertEqual(clean["metadata"]["access_token"], "[REDACTED]")
        self.assertEqual(clean["metadata"]["safe"], "ok")


if __name__ == "__main__":
    unittest.main()

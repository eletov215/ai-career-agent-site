from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if "tests" in str(Path(__file__).resolve()) else Path.cwd()
CHECKER = ROOT / "scripts/check_ai_bench_alice_final_result.py"


def sample_run(passed=8, errors=0, status="passed", provider_id="yandex-alice-ai-llm", scenario_repairs=0):
    return {
        "schema_version": "1.4",
        "benchmark_version": "1.4",
        "execution_mode": "live_or_mixed",
        "status": status,
        "dataset": {"case_count": 8, "version": "1.3.5"},
        "providers": [
            {
                "id": provider_id,
                "summary": {
                    "case_count": 8,
                    "passed_count": passed,
                    "error_count": errors,
                    "retry_count": 0,
                    "scenario_provenance_repair_count": scenario_repairs,
                    "forbidden_claim_count": 0,
                    "unsupported_number_count": 0,
                    "user_facing_technical_token_count": 0,
                    "claim_evidence_violation_count": 0,
                    "unsupported_impact_claim_count": 0,
                    "cover_letter_presentation_violation_count": 0,
                    "language_consistency_violation_count": 0,
                    "scenario_provenance_violation_count": 0,
                    "match_consistency_violation_count": 0,
                    "mean_quality_score": 1.0,
                    "mean_grounding_score": 1.0,
                    "p95_latency_ms": 1000,
                    "estimated_cost_usd": 0.01,
                },
            }
        ],
    }


class AliceFinalGateTests(unittest.TestCase):
    def _run(self, payload):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_pass(self):
        completed = self._run(sample_run())
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_safe_deterministic_scenario_repairs_are_audited_but_allowed(self):
        completed = self._run(sample_run(scenario_repairs=3))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("scenario_repairs=3", completed.stdout)

    def test_partial_rejected(self):
        completed = self._run(sample_run(passed=7, status="failed"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("machine safety gate not fully passed", completed.stderr)

    def test_wrong_provider_rejected(self):
        completed = self._run(sample_run(provider_id="yandex-alice-ai-llm-flash"))
        self.assertNotEqual(completed.returncode, 0)

    def test_safety_counter_rejected(self):
        payload = sample_run()
        payload["providers"][0]["summary"]["unsupported_impact_claim_count"] = 1
        completed = self._run(payload)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("non-zero safety counters", completed.stderr)

    def test_cover_letter_presentation_counter_rejected(self):
        payload = sample_run()
        payload["providers"][0]["summary"]["cover_letter_presentation_violation_count"] = 1
        completed = self._run(payload)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("non-zero safety counters", completed.stderr)

    def test_old_contract_is_rejected(self):
        payload = sample_run()
        payload["schema_version"] = "1.3"
        payload["benchmark_version"] = "1.3"
        payload["dataset"]["version"] = "1.3.4"
        completed = self._run(payload)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unexpected benchmark contract", completed.stderr)


if __name__ == "__main__":
    unittest.main()

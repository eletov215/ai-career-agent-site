from __future__ import annotations

import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_visible_gate_inputs_are_browser_upload_safe(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        required_visible = tuple(namespace["REQUIRED_VISIBLE"])
        hidden = [
            item
            for item in required_visible
            if any(part.startswith(".") for part in Path(item).parts)
        ]
        self.assertEqual(hidden, [])
        self.assertIn("evals/artifacts/README.md", required_visible)
        self.assertIn("evals/regressions/live-run-1.json", required_visible)
        self.assertIn("evals/regressions/live-run-2.json", required_visible)
        self.assertIn("evals/regressions/live-run-3.json", required_visible)
        self.assertIn("evals/regressions/live-run-4.json", required_visible)
        self.assertIn("evals/regressions/alice-final-run-1.json", required_visible)
        self.assertIn("evals/regressions/alice-final-run-4.json", required_visible)
        self.assertIn("evals/regressions/alice-final-run-5-human-review.json", required_visible)
        self.assertIn("evals/config/yandex-alice-final.json", required_visible)
        self.assertNotIn("evals/.gitignore", required_visible)
        self.assertNotIn("evals/artifacts/.gitkeep", required_visible)

    def test_live_controls_are_integrated_into_existing_ci_workflow(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        required_repository = tuple(namespace["REQUIRED_REPOSITORY"])
        self.assertIn(".github/workflows/ci.yml", required_repository)
        self.assertIn("scripts/check_ai_bench_live_result.py", required_repository)
        self.assertIn("scripts/check_ai_bench_alice_final_result.py", required_repository)
        self.assertNotIn(".github/workflows/ai-bench-live.yml", required_repository)

    def test_manual_live_job_runs_only_after_all_ordinary_ci_gates(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("run_ai_bench_live:", workflow)
        self.assertIn("type: boolean", workflow)
        self.assertIn("default: false", workflow)
        self.assertIn("ai-bench-yandex-live:", workflow)
        self.assertIn("name: AI-BENCH-001 Live Yandex", workflow)
        self.assertIn(
            "if: ${{ github.event_name == 'workflow_dispatch' && inputs.run_ai_bench_live == true }}",
            workflow,
        )
        self.assertIn("      - tests\n      - ai-bench-001", workflow)
        self.assertIn("AI_BENCH_YANDEX_API_KEY: ${{ secrets.AI_BENCH_YANDEX_API_KEY }}", workflow)
        self.assertIn("AI_BENCH_YANDEX_FOLDER_ID: ${{ secrets.AI_BENCH_YANDEX_FOLDER_ID }}", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertNotIn("uses: actions/upload-artifact@v4", workflow)
        self.assertIn("timeout-minutes: 45", workflow)
        self.assertIn("group: ai-bench-001-yandex-live", workflow)
        self.assertIn("AI_BENCH_OUTPUT_DIR: /tmp/ai-bench-yandex-live", workflow)
        self.assertNotIn("AI_BENCH_OUTPUT_DIR: ${{ runner.temp", workflow)

    def test_alice_final_job_is_manual_and_single_provider(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("run_ai_bench_alice_final:", workflow)
        self.assertIn("ai-bench-yandex-alice-final:", workflow)
        self.assertIn("name: AI-BENCH-001 Alice Final", workflow)
        self.assertIn("inputs.run_ai_bench_alice_final == true", workflow)
        self.assertIn("AI_BENCH_ALICE_FINAL_OUTPUT_DIR: /tmp/ai-bench-yandex-alice-final", workflow)
        self.assertIn("--config evals/config/yandex-alice-final.json", workflow)
        self.assertIn("scripts/check_ai_bench_alice_final_result.py", workflow)
        self.assertIn("grounded-v2.6", workflow)
        self.assertIn("scenario_provenance_repair_count", workflow)
        config = __import__("json").loads((ROOT / "evals/config/yandex-alice-final.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in config["providers"]], ["yandex-alice-ai-llm"])
        self.assertEqual(config["thresholds"]["max_error_rate"], 0.0)
        self.assertEqual(config["verification_scope"], "alice_ai_llm_final_candidate_v4")

    def test_job_level_env_context_validator_rejects_runner_context(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        validate = namespace["validate_job_level_env_contexts"]
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "bad.yml"
            workflow.write_text(
                "name: bad\n'on': push\njobs:\n  bad:\n    runs-on: ubuntu-latest\n    env:\n      OUT: ${{ runner.temp }}/x\n    steps:\n      - run: echo ok\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                validate(workflow)

    def test_job_level_env_context_validator_allows_runner_in_step_env(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        validate = namespace["validate_job_level_env_contexts"]
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "good.yml"
            workflow.write_text(
                "name: good\n'on': push\njobs:\n  ok:\n    runs-on: ubuntu-latest\n    steps:\n      - name: allowed\n        env:\n          OUT: ${{ runner.temp }}/x\n        run: echo \"$OUT\"\n",
                encoding="utf-8",
            )
            validate(workflow)

    def test_current_workflow_job_env_contexts_are_valid(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        validate = namespace["validate_job_level_env_contexts"]
        validate(ROOT / ".github/workflows/ci.yml")


    def test_grounded_v26_contract_is_package_gated(self) -> None:
        version = (ROOT / "evals/VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, "1.6.0")
        vacancy_schema = (ROOT / "evals/schemas/vacancy_match.schema.json").read_text(encoding="utf-8")
        self.assertNotIn('"match_score"', vacancy_schema)
        for schema in (ROOT / "evals/schemas").glob("*.json"):
            self.assertIn("^[a-z][0-9]+$", schema.read_text(encoding="utf-8"), schema.name)

    def test_visible_artifact_scaffold_exists(self) -> None:
        readme = ROOT / "evals/artifacts/README.md"
        self.assertTrue(readme.is_file())
        self.assertIn("must not be committed", readme.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

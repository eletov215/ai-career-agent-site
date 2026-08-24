from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from evals.ai_bench.dataset import load_dataset
from evals.ai_bench.schema import validate_instance
from evals.ai_bench.scoring import score_case

ROOT = Path(__file__).resolve().parents[1]


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.cases, _ = load_dataset(ROOT / "evals/fixtures/manifest.json")

    def test_reference_outputs_pass_strict_gate(self) -> None:
        thresholds = {
            "min_required_path_coverage": 1.0,
            "min_grounding_score": 1.0,
            "min_quality_score": 1.0,
            "max_forbidden_claims": 0,
            "max_invalid_evidence_ids": 0,
            "max_unsupported_numbers": 0,
        }
        for case in self.cases:
            with self.subTest(case=case.case_id):
                content = json.loads((ROOT / "evals/expected/reference" / f"{case.case_id}.json").read_text(encoding="utf-8"))
                score = score_case(case, content, thresholds)
                self.assertTrue(score["passed"], score)

    def test_forbidden_claim_is_a_hard_failure(self) -> None:
        case = next(item for item in self.cases if item.case_id == "resume-analysis-ru-01")
        content = json.loads((ROOT / "evals/expected/reference" / f"{case.case_id}.json").read_text(encoding="utf-8"))
        content["summary"] += " Кандидат руководил командой."
        score = score_case(case, content, {"max_forbidden_claims": 0})
        self.assertFalse(score["passed"])
        self.assertIn("fake_leadership", score["forbidden_claims"])

    def test_invalid_evidence_is_detected(self) -> None:
        case = next(item for item in self.cases if item.case_id == "cover-letter-en-01")
        content = json.loads((ROOT / "evals/expected/reference" / f"{case.case_id}.json").read_text(encoding="utf-8"))
        content["evidence_ids"].append("invented-source")
        score = score_case(case, content, {"max_invalid_evidence_ids": 0})
        self.assertFalse(score["passed"])
        self.assertIn("invented-source", score["invalid_evidence_ids"])

    def test_schema_rejects_additional_property(self) -> None:
        schema = json.loads((ROOT / "evals/schemas/cover_letter.schema.json").read_text(encoding="utf-8"))
        content = json.loads((ROOT / "evals/expected/reference/cover-letter-en-01.json").read_text(encoding="utf-8"))
        content["invented"] = True
        errors = validate_instance(content, schema)
        self.assertTrue(any("additional property" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

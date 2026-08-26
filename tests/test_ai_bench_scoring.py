from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from evals.ai_bench.dataset import load_dataset
from evals.ai_bench.schema import validate_instance
from evals.ai_bench.scoring import score_case

ROOT = Path(__file__).resolve().parents[1]

STRICT_THRESHOLDS = {
    "min_required_path_coverage": 1.0,
    "min_grounding_score": 1.0,
    "min_quality_score": 1.0,
    "max_forbidden_claims": 0,
    "max_invalid_evidence_ids": 0,
    "max_unsupported_numbers": 0,
    "max_user_facing_technical_tokens": 0,
    "max_claim_evidence_violations": 0,
    "max_unsupported_impact_claims": 0,
    "min_required_unverified_coverage": 1.0,
    "min_required_caveat_coverage": 1.0,
    "max_match_consistency_violations": 0,
}


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.cases, _ = load_dataset(ROOT / "evals/fixtures/manifest.json")
        cls.by_id = {case.case_id: case for case in cls.cases}
        cls.regressions = json.loads((ROOT / "evals/regressions/live-run-1.json").read_text(encoding="utf-8"))

    def _reference(self, case_id: str) -> dict:
        return json.loads((ROOT / "evals/expected/reference" / f"{case_id}.json").read_text(encoding="utf-8"))

    def test_reference_outputs_pass_strict_gate(self) -> None:
        for case in self.cases:
            with self.subTest(case=case.case_id):
                score = score_case(case, self._reference(case.case_id), STRICT_THRESHOLDS)
                self.assertTrue(score["passed"], score)
                self.assertEqual(score["quality_score"], 1.0)

    def test_sourced_hypothetical_numbers_are_allowed(self) -> None:
        case = self.by_id["interview-en-01"]
        content = self._reference(case.case_id)
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertEqual(score["unsupported_numbers"], [])
        self.assertNotIn("unsupported_numbers", score["gate_failures"])
        joined = json.dumps(content, ensure_ascii=False)
        for token in self.regressions["patterns"]["allowed_hypothetical_numbers"]:
            numeric = token.split()[0]
            self.assertIn(numeric, joined)

    def test_unsourced_number_is_reported_at_scalar_leaf_path(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        content["recommendation"] += " Complete 99 exercises first."
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["unsupported_numbers"], [{"path": "$.recommendation", "value": "99"}])
        self.assertIn("unsupported_numbers", score["gate_failures"])

    def test_forbidden_claim_is_a_hard_failure(self) -> None:
        case = self.by_id["resume-analysis-ru-01"]
        content = self._reference(case.case_id)
        content["summary"] += " Кандидат руководил командой."
        score = score_case(case, content, {"max_forbidden_claims": 0})
        self.assertFalse(score["passed"])
        self.assertIn("fake_leadership", score["forbidden_claims"])

    def test_invalid_evidence_is_detected(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["evidence_ids"].append("invented-source")
        score = score_case(case, content, {"max_invalid_evidence_ids": 0})
        self.assertFalse(score["passed"])
        self.assertIn("invented-source", score["invalid_evidence_ids"])

    def test_schema_requires_raw_evidence_id_format(self) -> None:
        schema = json.loads((ROOT / "evals/schemas/interview_questions.schema.json").read_text(encoding="utf-8"))
        content = self._reference("interview-ru-01")
        content["questions"][0]["evidence_ids"] = ["[c1]"]
        errors = validate_instance(content, schema)
        self.assertTrue(any("pattern" in error for error in errors), errors)

    def test_live_run_technical_metadata_is_blocked_from_user_facing_text(self) -> None:
        for sample in self.regressions["patterns"]["user_facing_technical_metadata"]:
            case = self.by_id[sample["case_id"]]
            with self.subTest(case=case.case_id, sample=sample["text"]):
                content = self._reference(case.case_id)
                if case.task == "cover_letter":
                    content["paragraphs"][1]["text"] = sample["text"]
                else:
                    content["summary"] = sample["text"]
                score = score_case(case, content, {"max_user_facing_technical_tokens": 0})
                self.assertFalse(score["passed"])
                self.assertTrue(score["user_facing_technical_tokens"], score)
                self.assertIn("user_facing_technical_tokens", score["gate_failures"])

    def test_live_run_unsupported_impact_is_blocked_even_without_number(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][2]["text"] = self.regressions["patterns"]["unsupported_impact"]
        content["paragraphs"][2]["evidence_ids"] = ["c4"]
        score = score_case(case, content, {"max_unsupported_impact_claims": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["unsupported_impact_claim_count"], 1)
        self.assertIn("unsupported_impact_claims", score["gate_failures"])

    def test_candidate_fit_paragraph_cannot_be_supported_only_by_vacancy_requirement(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["evidence_ids"] = ["v2"]
        score = score_case(case, content, {"max_claim_evidence_violations": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["claim_evidence_violation_count"], 1)
        self.assertIn("claim_evidence", score["gate_failures"])

    def test_resume_unverified_fact_requires_structured_evidence(self) -> None:
        case = self.by_id["resume-analysis-en-01"]
        content = self._reference(case.case_id)
        content["facts_not_verified"] = [{"fact": "Production Python is not verified.", "evidence_ids": ["e1"]}]
        score = score_case(case, content, {"min_required_unverified_coverage": 1.0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing_unverified_evidence_ids"], ["e5"])
        self.assertIn("unverified_coverage", score["gate_failures"])

    def test_cover_letter_caveat_must_cover_unverified_requirement(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        content["caveats"][0]["evidence_ids"] = ["v3"]
        score = score_case(case, content, {"min_required_caveat_coverage": 1.0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing_caveat_evidence_ids"], ["c5"])
        self.assertIn("caveat_coverage", score["gate_failures"])

    def test_vacancy_match_score_is_derived_deterministically(self) -> None:
        ru_case = self.by_id["vacancy-match-ru-01"]
        en_case = self.by_id["vacancy-match-en-01"]
        ru_score = score_case(ru_case, self._reference(ru_case.case_id), STRICT_THRESHOLDS)
        en_score = score_case(en_case, self._reference(en_case.case_id), STRICT_THRESHOLDS)
        self.assertEqual(ru_score["match_evaluation"]["deterministic_match_score"], 67)
        self.assertEqual(en_score["match_evaluation"]["deterministic_match_score"], 71)
        self.assertEqual(ru_score["match_evaluation"]["deterministic_verdict"], "partial")
        self.assertEqual(en_score["match_evaluation"]["deterministic_verdict"], "partial")
        self.assertNotIn("match_score", self._reference(ru_case.case_id))

    def test_live_run_wrong_requirement_status_is_detected(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        moved = next(item for item in content["matched_requirements"] if item["requirement_id"] == "v4")
        content["matched_requirements"] = [item for item in content["matched_requirements"] if item["requirement_id"] != "v4"]
        content["gaps"].append(moved)
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertIn("expected_matched_got_gap", reasons)
        self.assertIn("match_consistency", score["gate_failures"])

    def test_live_run_duplicate_requirement_is_detected(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        content["matched_requirements"].append(deepcopy(content["matched_requirements"][0]))
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertIn("duplicate_classification", reasons)

    def test_match_requirement_must_cite_vacancy_and_candidate_evidence(self) -> None:
        case = self.by_id["vacancy-match-ru-01"]
        content = self._reference(case.case_id)
        content["matched_requirements"][0]["evidence_ids"] = ["c1"]
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertTrue(any("vacancy_requirement_evidence" in reason for reason in reasons), reasons)

    def test_schema_rejects_additional_property(self) -> None:
        schema = json.loads((ROOT / "evals/schemas/cover_letter.schema.json").read_text(encoding="utf-8"))
        content = self._reference("cover-letter-en-01")
        content["invented"] = True
        errors = validate_instance(content, schema)
        self.assertTrue(any("additional property" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

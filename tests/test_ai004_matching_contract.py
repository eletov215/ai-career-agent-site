"""AI004-M03: synthetic-only grounding, scoring and adversarial quality tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from domain.vacancy_match import MATCH_VERSION, MAX_REQUIREMENTS
from services.matching_input import project_resume_version, project_saved_vacancy
from services.matching_contract import (
    CLASSIFICATION_VERSION, REQUIREMENT_POLICY_VERSION, WEIGHT_POLICY_VERSION,
    ClassificationContractError, build_classification_contract,
)
from services.matching_validation import validate_classification


SUITE = json.loads(
    (Path(__file__).resolve().parents[1] / "quality/ai004/matching_golden_v1.json")
    .read_text(encoding="utf-8")
)
CASES = {case["id"]: case for case in SUITE["cases"]}


def _resume(answers):
    return project_resume_version({
        "snapshot": {
            "schemaVersion": 1, "answers": {
                **answers, "name": "PRIVATE IDENTITY",
                "contacts": "PRIVATE CONTACT ADDRESS",
            },
            "messages": ["PRIVATE CHAT HISTORY"],
        },
    })


def _vacancy(requirements, title="Backend engineer"):
    return project_saved_vacancy({
        "snapshot": {
            "snapshot_version": "saved-vacancy-v1",
            "title": title, "company": "Synthetic Employer",
            "requirements": requirements,
            "description": "Sample description",
            "source_records": [{"url": "https://private.invalid"}],
            "note": "PRIVATE PERSONAL NOTE",
        }
    })


def _contract(case):
    return build_classification_contract(
        _resume(case["resume_answers"]),
        _vacancy(case["vacancy"]["requirements"], case["vacancy"]["title"]),
        source_complete=True,
    )


def _model(case, contract):
    return {
        "contract_version": CLASSIFICATION_VERSION,
        "source_hash": contract.source_hash,
        "classifications": copy.deepcopy(case["classifications"]),
    }


def _validate(case, content=None):
    contract = _contract(case)
    payload = _model(case, contract) if content is None else content
    return validate_classification(json.dumps(payload, ensure_ascii=False), contract)


@pytest.mark.parametrize("case", SUITE["cases"], ids=lambda item: item["id"])
def test_golden_synthetic_reports_have_fixed_scores_and_source_quotations(case):
    contract = _contract(case)
    assert len(contract.source_hash) == 64
    assert contract.version == CLASSIFICATION_VERSION
    assert set(contract.schema["required"]) == {
        "contract_version", "source_hash", "classifications"
    }
    result = _validate(case)
    summary = result["summary"]
    assert summary["policy_version"] == MATCH_VERSION
    for name, expected in case["expected"].items():
        assert summary[name] == expected
    assert summary["requirement_count"] == len(case["classifications"])
    assert result["presentation"] == "source_quotes_and_code_labels"
    assert result["source_hash"] == contract.source_hash
    assert result["resume_hash"] == contract.resume_hash
    assert result["vacancy_hash"] == contract.vacancy_hash
    assert [r["requirement_id"] for r in result["requirements"]] == [
        item.requirement_id for item in contract.requirements
    ]
    for requirement in result["requirements"]:
        assert requirement["source_id"] == "vacancy.requirements"
        assert requirement["requirement"] in case["vacancy"]["requirements"]
        for evidence in requirement["candidate_evidence"]:
            source = {fact["id"]: fact["text"] for fact in contract.candidate_facts}
            assert evidence["quote"] in source[evidence["id"]]
    report_text = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "PRIVATE CONTACT ADDRESS", "PRIVATE IDENTITY", "PRIVATE CHAT HISTORY",
        "PRIVATE PERSONAL NOTE", "https://private.invalid",
    ):
        assert forbidden not in report_text


def test_no_score_can_be_calculated_without_verified_source_completeness():
    resume = _resume({"skills": "Python"})
    vacancy = _vacancy("Python")
    for flag in (False, None, 1, "true"):
        with pytest.raises(ClassificationContractError,
                           match="^source_completeness_unverified$"):
            build_classification_contract(
                resume, vacancy, source_complete=flag
            )
    assert SUITE["synthetic"] is True
    assert SUITE["version"] == "ai004-m03-synthetic-quality-v1"


@pytest.mark.parametrize("requirements,reason", [
    ("", "insufficient_requirements"),
    ("\n  ; \n", "insufficient_requirements"),
    ("Python\n python ", "ambiguous_requirements"),
    ("Python\n" + "X" * 513, "unsupported_requirements"),
    ("\n".join(f"Skill {i}" for i in range(MAX_REQUIREMENTS + 1)),
     "unsupported_requirements"),
])
def test_unscoreable_or_ambiguous_requirements_fail_closed(requirements, reason):
    with pytest.raises(ClassificationContractError, match=f"^{reason}$"):
        build_classification_contract(
            _resume({"skills": "Python"}), _vacancy(requirements),
            source_complete=True,
        )


def test_requirements_from_description_are_not_assumed_complete():
    with pytest.raises(ClassificationContractError, match="insufficient_requirements"):
        build_classification_contract(
            _resume({"skills": "Python"}),
            project_saved_vacancy({"snapshot": {
                "snapshot_version": "saved-vacancy-v1",
                "title": "Python developer",
                "description": "Must have Python", "requirements": "",
            }}),
            source_complete=True,
        )


def test_64_distinct_requirements_supported_without_silent_truncation():
    text = "\n".join(f"Skill-{i}" for i in range(MAX_REQUIREMENTS))
    contract = build_classification_contract(
        _resume({"skills": "Python"}), _vacancy(text),
        source_complete=True,
    )
    assert len(contract.requirements) == MAX_REQUIREMENTS
    assert contract.requirements[-1].requirement_id == "req-064"
    assert contract.schema["properties"]["classifications"]["maxItems"] == MAX_REQUIREMENTS


def test_requirement_source_is_model_independent_and_weight_policy_is_fixed():
    contract = _contract(CASES["ru-positive-and-unknown"])
    assert [row.importance for row in contract.requirements] == [
        "mandatory", "mandatory", "preferred"
    ]
    assert [row.weight for row in contract.requirements] == [2, 2, 1]
    assert REQUIREMENT_POLICY_VERSION and WEIGHT_POLICY_VERSION
    assert "PRIVATE IDENTITY" not in repr(contract)
    assert "Python, PostgreSQL" not in repr(contract)


def test_source_mutation_cannot_change_a_built_contract():
    case = CASES["ru-positive-and-unknown"]
    r = _resume(case["resume_answers"])
    v = _vacancy(case["vacancy"]["requirements"])
    contract = build_classification_contract(r, v, source_complete=True)
    original = (contract.source_hash, contract.candidate_facts,
                tuple(x.text for x in contract.requirements))
    r["facts"][0]["text"] = "invented mutation"
    v["fields"]["requirements"] = "different vacancy"
    assert original == (contract.source_hash, contract.candidate_facts,
                        tuple(x.text for x in contract.requirements))


@pytest.mark.parametrize("tamper", ["resume", "vacancy", "injected"])
def test_projection_mutation_does_not_bypass_integrity(tamper):
    r = _resume({"skills": "Python"})
    v = _vacancy("Python")
    if tamper == "resume":
        r["facts"][0]["text"] = "invented"
    elif tamper == "vacancy":
        v["fields"]["requirements"] = "invented"
    else:
        v["fields"]["contacts"] = "private"
    with pytest.raises(ClassificationContractError,
                       match="^invalid_projection$"):
        build_classification_contract(r, v, source_complete=True)


def test_source_hash_changes_when_resume_or_vacancy_changes():
    base = build_classification_contract(_resume({"skills": "Python"}),
                                         _vacancy("Python"), source_complete=True)
    changed_resume = build_classification_contract(_resume({"skills": "Python, Go"}),
                                                   _vacancy("Python"), source_complete=True)
    changed_vacancy = build_classification_contract(_resume({"skills": "Python"}),
                                                    _vacancy("Python\nGo"), source_complete=True)
    assert len({base.source_hash, changed_resume.source_hash,
                changed_vacancy.source_hash}) == 3


def test_provider_response_order_cannot_reorder_trusted_requirements():
    case = CASES["ru-positive-and-unknown"]
    c = _contract(case)
    d = _model(case, c)
    d["classifications"].reverse()
    result = validate_classification(json.dumps(d), c)
    assert [row["requirement_id"] for row in result["requirements"]] == [
        "req-001", "req-002", "req-003"
    ]
    assert result["summary"]["score_percent"] == 80


def _mutated_payload(name):
    case = (CASES["en-explicit-negative"]
            if name in {"negated_matched_support", "unsupported_explicit_mismatch"}
            else CASES["ru-quantified-match"]
            if name == "unsupported_numeric_years"
            else CASES["ru-positive-and-unknown"])
    contract = _contract(case)
    body = _model(case, contract)
    rows = body["classifications"]
    if name == "provider_percent":
        body["match_score"] = 100
    elif name == "provider_verdict":
        body["verdict"] = "strong"
    elif name == "unsupported_quote":
        rows[0]["candidate_evidence"][0]["quote"] = "FAKE CERTIFIED EXPERT"
    elif name == "wrong_evidence_id":
        rows[0]["candidate_evidence"][0]["id"] = "resume.private_name"
    elif name == "missing_requirement":
        rows.pop()
    elif name == "repeated_requirement":
        rows[-1]["requirement_id"] = "req-001"
    elif name == "invented_requirement":
        rows[-1]["requirement_id"] = "req-999"
    elif name == "stale_source_hash":
        body["source_hash"] = "0" * 64
    elif name == "unverified_with_evidence":
        rows[2]["candidate_evidence"] = [{"id": "resume.skills", "quote": "Python"}]
    elif name == "no_matching_evidence":
        rows[1]["candidate_evidence"] = [{"id": "resume.skills", "quote": "Python"}]
    elif name == "unsupported_explicit_mismatch":
        rows[0]["status"] = "mismatch"
    elif name == "unsupported_numeric_years":
        rows[0]["candidate_evidence"][0]["quote"] = "Python"
    elif name == "negated_matched_support":
        rows[1]["status"] = "matched"
    elif name == "provider_importance":
        rows[0]["importance"] = "preferred"
    elif name == "provider_weight":
        rows[0]["weight"] = 100
    elif name == "extra_provider_prose":
        rows[0]["explanation"] = "guaranteed acceptance at 100 percent"
    else:
        assert name == "duplicated_json_keys"
    return case, contract, body


@pytest.mark.parametrize("mutation", SUITE["mutation_ids"])
def test_adversarial_mutations_are_rejected_with_fixed_safe_errors(mutation):
    case, contract, body = _mutated_payload(mutation)
    if mutation == "duplicated_json_keys":
        raw = (
            '{"contract_version":"%s","source_hash":"%s",'
            '"source_hash":"%s","classifications":[]}'
        ) % (CLASSIFICATION_VERSION, contract.source_hash, contract.source_hash)
    else:
        raw = json.dumps(body, ensure_ascii=False)
    with pytest.raises(ClassificationContractError) as exc:
        validate_classification(raw, contract)
    assert str(exc.value) in {
        "invalid_output_schema", "stale_source", "unsupported_evidence",
        "unsupported_classification", "invalid_candidate_reference",
        "invalid_requirement_reference", "incomplete_classifications",
    }
    assert "PRIVATE" not in str(exc.value)


@pytest.mark.parametrize("raw", [
    '{"contract_version":NaN}',
    "{broken_json",
    "[]",
    "{}",
    "",
    '{"contract_version":"invalid"}',
])
def test_malformed_provider_json_never_becomes_a_score(raw):
    with pytest.raises(ClassificationContractError):
        validate_classification(raw, _contract(CASES["en-all-unknown"]))


def test_false_positive_same_word_with_missing_years_is_rejected():
    c = _contract(CASES["ru-quantified-match"])
    model = _model(CASES["ru-quantified-match"], c)
    model["classifications"][0]["candidate_evidence"][0]["quote"] = "Python"
    with pytest.raises(ClassificationContractError,
                       match="^unsupported_classification$"):
        validate_classification(json.dumps(model), c)


def test_unknown_is_not_mismatch_and_cannot_yield_strong():
    report = _validate(CASES["en-all-unknown"])
    assert report["summary"]["score_percent"] == 0
    assert report["summary"]["mismatch_weight"] == 0
    assert report["summary"]["unverified_weight"] == 4
    assert report["summary"]["verdict"] != "strong"


def test_provider_can_never_select_its_own_requirement_or_weight():
    contract = _contract(CASES["en-explicit-negative"])
    assert set(contract.schema["properties"]["classifications"]["items"]["properties"]) == {
        "requirement_id", "status", "candidate_evidence"
    }
    assert contract.schema["additionalProperties"] is False
    assert contract.schema["properties"]["classifications"]["items"]["additionalProperties"] is False
    assert contract.schema["properties"]["source_hash"]["enum"] == [contract.source_hash]


def test_zero_paid_calls_and_no_external_side_effects(monkeypatch):
    # Pure functions only: deliberately do not initialise the AI provider.
    import domain.ai
    assert domain.ai.REAL_DATA_SUPPORTED is False
    assert _validate(CASES["en-explicit-negative"])["summary"]["score_percent"] == 60

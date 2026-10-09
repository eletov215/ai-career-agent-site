"""AI004-M04A synthetic-only cache identity and signed snapshot regressions."""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from services.matching_contract import (
    CLASSIFICATION_VERSION, ClassificationContract,
    build_classification_contract,
)
from services.matching_input import project_resume_version, project_saved_vacancy
from services.matching_validation import validate_classification
from services.matching_cache_keys import (
    CACHE_KEY_VERSION, MatchCacheKeyError, build_cache_address,
    build_operation_hash, seal_validated_result, verify_sealed_result,
)

SECRET = b"synthetic-test-not-a-production-secret-1234567"
OTHER_SECRET = b"synthetic-test-not-a-production-secret-7654321"
OWNER_1 = "00000000-0000-0000-0000-000000000001"
OWNER_2 = "00000000-0000-0000-0000-000000000002"
VERSION_1 = "00000000-0000-0000-0000-000000000003"
VERSION_2 = "00000000-0000-0000-0000-000000000004"
VACANCY_A = "a" * 64
VACANCY_B = "b" * 64


def _source(*, skills="Python and PostgreSQL", requirement="Python"):
    r = project_resume_version({"snapshot": {
        "schemaVersion": 1, "answers": {
            "role": "Python developer", "skills": skills,
            "contacts": "private@example.test", "name": "PRIVATE PERSON",
        },
    }})
    v = project_saved_vacancy({"snapshot": {
        "snapshot_version": "saved-vacancy-v1",
        "title": "Backend engineer", "company": "Synthetic company",
        "description": "An internal synthetic role",
        "requirements": requirement,
        "note": "PRIVATE NOTES", "source_records": [
            {"url": "https://private.invalid/vacancy"}
        ],
    }})
    return build_classification_contract(r, v, source_complete=True)


def _address(*, owner=OWNER_1, version=VERSION_1,
             identity=VACANCY_A, contract=None, secret=SECRET):
    return build_cache_address(
        secret=secret, user_id=owner, resume_version_id=version,
        vacancy_identity_hash=identity,
        contract=contract or _source(),
    )


def _result(contract):
    fact = next(row for row in contract.candidate_facts if row["id"] == "resume.skills")
    response = {
        "contract_version": CLASSIFICATION_VERSION,
        "source_hash": contract.source_hash,
        "classifications": [{
            "requirement_id": "req-001", "status": "matched",
            "candidate_evidence": [{"id": fact["id"], "quote": "Python"}],
        }],
    }
    return validate_classification(json.dumps(response), contract)


def test_identical_inputs_have_same_content_cache_but_not_same_operation_nonce():
    first = _address()
    second = _address()
    assert first == second
    assert first.version == CACHE_KEY_VERSION
    assert first.cache_key_hash != first.request_hash
    assert len(first.cache_key_hash) == len(first.request_hash) == 64

    same = build_operation_hash(secret=SECRET, address=first,
                                owner_action_nonce="click-0001")
    again = build_operation_hash(secret=SECRET, address=second,
                                 owner_action_nonce="click-0001")
    fresh = build_operation_hash(secret=SECRET, address=second,
                                 owner_action_nonce="click-0002")
    assert same == again
    assert fresh != same
    assert same not in (first.cache_key_hash, first.request_hash)


@pytest.mark.parametrize("changes", [
    {"owner": OWNER_2},
    {"version": VERSION_2},
    {"identity": VACANCY_B},
    {"contract": _source(skills="Python and Go")},
    {"contract": _source(requirement="Python; Docker")},
    {"secret": OTHER_SECRET},
])
def test_cache_identity_changes_across_tenant_version_vacancy_source_or_secret(changes):
    base = _address()
    other = _address(**changes)
    assert base.cache_key_hash != other.cache_key_hash
    assert base.request_hash != other.request_hash


def test_synthetic_result_can_be_sealed_and_verified_without_provider():
    contract = _source()
    address = _address(contract=contract)
    report = _result(contract)
    seal = seal_validated_result(secret=SECRET, address=address, report=report)
    assert len(seal) == 64
    assert verify_sealed_result(secret=SECRET, address=address, report=report, signature=seal)
    assert not verify_sealed_result(secret=OTHER_SECRET, address=address,
                                    report=report, signature=seal)


@pytest.mark.parametrize("mutation", [
    "alter_score", "alter_quote", "change_source_hash",
    "drop_requirements", "provider_injected_verdict", "change_version",
])
def test_mutated_saved_report_is_rejected_as_cache_hit(mutation):
    contract = _source()
    address = _address(contract=contract)
    original = _result(contract)
    seal = seal_validated_result(secret=SECRET, address=address, report=original)
    tampered = copy.deepcopy(original)
    if mutation == "alter_score":
        tampered["summary"]["score_percent"] = 99
    elif mutation == "alter_quote":
        tampered["requirements"][0]["candidate_evidence"][0]["quote"] = "invented skill"
    elif mutation == "change_source_hash":
        tampered["source_hash"] = "0" * 64
    elif mutation == "drop_requirements":
        tampered["requirements"] = []
    elif mutation == "provider_injected_verdict":
        tampered["provider_verdict"] = "guaranteed offer"
    else:
        tampered["classification_version"] = "unapproved"
    assert not verify_sealed_result(
        secret=SECRET, address=address, report=tampered, signature=seal
    )


def test_report_signature_is_bound_to_exact_owner_scoped_cache_address():
    contract = _source()
    original = _address(contract=contract)
    report = _result(contract)
    seal = seal_validated_result(secret=SECRET, address=original, report=report)
    other_user = _address(owner=OWNER_2, contract=contract)
    assert not verify_sealed_result(secret=SECRET, address=other_user,
                                    report=report, signature=seal)


def test_keys_and_repr_do_not_include_source_or_account_identifiers():
    contract = _source()
    address = _address(contract=contract)
    output = repr(address)
    for forbidden in (
        OWNER_1, VERSION_1, VACANCY_A, contract.source_hash,
        address.cache_key_hash, address.request_hash,
        "Python", "PRIVATE PERSON", "private@example.test", "PRIVATE NOTES",
    ):
        assert forbidden not in output
    assert output == "MatchCacheAddress(version='ai004-owner-match-cache-v1')"


@pytest.mark.parametrize("bad", [
    b"", b"short", "not_bytes", None, bytearray(40),
])
def test_unknown_or_short_secret_never_creates_valid_fingerprint(bad):
    with pytest.raises(MatchCacheKeyError, match="^cache_key_unavailable$"):
        _address(secret=bad)


@pytest.mark.parametrize("key_fields", [
    {"owner": "not-a-uuid"},
    {"owner": "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"},
    {"version": "not-a-uuid"},
    {"identity": "bad"},
    {"identity": "G" * 64},
    {"contract": replace(_source(), version="unsupported")},
    {"contract": replace(_source(), source_hash="broken")},
    {"contract": replace(_source(), resume_hash="broken")},
    {"contract": replace(_source(), vacancy_hash="broken")},
    {"contract": "untrusted"},
])
def test_untrusted_address_parts_are_rejected_with_safe_error(key_fields):
    with pytest.raises(MatchCacheKeyError, match="^invalid_cache_source$"):
        _address(**key_fields)


@pytest.mark.parametrize("nonce", [
    "", "bad", "x" * 129, "with space", "bad\nnonce",
    False, 12345678, None,
])
def test_invalid_user_operation_nonce_is_rejected(nonce):
    with pytest.raises(MatchCacheKeyError, match="^invalid_operation_nonce$"):
        build_operation_hash(secret=SECRET, address=_address(),
                             owner_action_nonce=nonce)


def test_malformed_cached_signature_never_serves_result():
    contract = _source()
    address = _address(contract=contract)
    report = _result(contract)
    assert not verify_sealed_result(secret=SECRET, address=address,
                                    report=report, signature="0" * 64)
    assert not verify_sealed_result(secret=SECRET, address=address,
                                    report=report, signature=None)
    assert not verify_sealed_result(secret=SECRET, address=address,
                                    report=report, signature="anything")


def test_versioned_scoring_policy_is_part_of_cache_identity(monkeypatch):
    contract = _source()
    baseline = _address(contract=contract)
    monkeypatch.setattr("services.matching_cache_keys.MATCH_VERSION",
                        "synthetic-future-policy")
    changed = _address(contract=contract)
    assert changed.cache_key_hash != baseline.cache_key_hash
    assert changed.request_hash != baseline.request_hash


def test_no_database_calls_or_live_ai_admission():
    from domain.ai import REAL_DATA_SUPPORTED
    assert REAL_DATA_SUPPORTED is False
    c = _source()
    _ = _address(contract=c)
    assert _result(c)["summary"]["score_percent"] == 100

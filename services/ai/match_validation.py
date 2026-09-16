"""Strict fixed-fixture classification boundary; not a general truth oracle.

Accepted AI-001 prompts/schemas are unchanged. Model prose and verdicts are NOT
used as user-facing evidence. Canonical explanations are composed from verbatim
source facts and explicit evidence status. This prevents prose from overriding
an unverified requirement or supplying a fabricated percentage.
"""
import hashlib
import json
from domain.vacancy_match import FIXTURE_IDS, MatchError, MatchRequirement, calculate_match
from services.ai.registry import ContractError, validate_output


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_match(content, fixture, schema):
    if (fixture.get("case_id") not in FIXTURE_IDS or fixture.get("synthetic") is not True
            or fixture.get("task") != "vacancy_match"):
        raise ContractError("Unsupported match fixture")
    try:
        output = validate_output(json.dumps(content, ensure_ascii=False, allow_nan=False), schema)
        facts = {f["id"]: f for f in fixture["source_facts"]}
        specs = {r["requirement_id"]: r for r in fixture["match_requirements"]}
        if len(facts) != len(fixture["source_facts"]) or len(specs) != len(fixture["match_requirements"]):
            raise ContractError("Duplicate source identity")
        seen = {}
        for section, actual in (("matched_requirements", "matched"), ("gaps", "gap")):
            for row in output[section]:
                rid = row["requirement_id"]
                spec = specs.get(rid)
                if rid in seen or spec is None or actual != spec["expected_status"]:
                    raise ContractError("Invalid fixed-fixture classification")
                expected = {rid, *spec["candidate_evidence_ids"]}
                evidence = row["evidence_ids"]
                if (len(evidence) != len(set(evidence)) or set(evidence) != expected
                        or not expected <= facts.keys() or facts[rid]["kind"] != "vacancy"
                        or any(facts[c]["kind"] != "candidate" for c in spec["candidate_evidence_ids"])):
                    raise ContractError("Unlinked match evidence")
                # Classifications are checked against the pinned test cases.
                # An unverified input is not reinterpreted as lack of ability.
                seen[rid] = "matched" if actual == "matched" else "unverified"
        if seen.keys() != specs.keys():
            raise ContractError("Incomplete match requirements")
        rows = []
        for rid, spec in specs.items():
            rows.append({"requirement_id": rid, "requirement": facts[rid]["text"],
                "importance": spec["importance"], "weight": spec["weight"], "status": seen[rid],
                "evidence": [{"id": cid, "text": facts[cid]["text"], "kind": "candidate"}
                             for cid in spec["candidate_evidence_ids"]]})
        calculated = calculate_match([MatchRequirement(r["requirement_id"], r["importance"], r["weight"], r["status"]) for r in rows])
        # Do not persist/reuse provider prose, percentages, or verdict. All
        # displayed claims below are source extracts or deterministic labels.
        return {"summary": calculated, "requirements": rows,
                "presentation": "source_quotes_and_code_labels", "language": fixture["language"]}
    except (ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("Invalid match contract") from None

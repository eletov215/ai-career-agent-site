"""AI004-M03: evidence-only classification validator and deterministic score.

Only trusted M01 source excerpts reach a report; model-authored prose,
percentages, verdicts, requirement lists and importance never do. This checks
literal quotation, identity, completeness, basic lexical/number safeguards,
and explicit negative evidence. It is NOT a semantic truth oracle and is not
an authorization for real-data AI or paid provider dispatch.
"""
from __future__ import annotations

import json
import re
from typing import Any

from domain.vacancy_match import MatchError, MatchRequirement, calculate_match
from services.matching_contract import (
    CLASSIFICATION_VERSION, MAX_CANDIDATE_REFERENCES,
    MAX_PROVIDER_OUTPUT_BYTES, MAX_QUOTE_CHARS,
    ClassificationContract, ClassificationContractError,
)
from services.matching_prefilter import _tokens

_NUMBER = re.compile(r"(?<!\w)[0-9]+(?:[.,][0-9]+)?(?!\w)", re.UNICODE)
_NEGATION = re.compile(
    r"(?<!\w)(?:no|not|without|none|never|нет|не|без|отсутствует)(?!\w)",
    re.IGNORECASE,
)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ClassificationContractError("invalid_output_schema")
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise ClassificationContractError("invalid_output_schema")


def _decode(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_PROVIDER_OUTPUT_BYTES:
        raise ClassificationContractError("invalid_output_schema")
    try:
        result = json.loads(raw, object_pairs_hook=_unique_pairs,
                            parse_constant=_reject_number)
    except (ValueError, UnicodeError):
        raise ClassificationContractError("invalid_output_schema") from None
    if not isinstance(result, dict) or set(result) != {
        "contract_version", "source_hash", "classifications"
    }:
        raise ClassificationContractError("invalid_output_schema")
    return result


def _check_quote(text: Any, source: str) -> None:
    if (not isinstance(text, str) or not 2 <= len(text) <= MAX_QUOTE_CHARS
            or not text.strip() or text not in source):
        raise ClassificationContractError("unsupported_evidence")


def validate_classification(raw: str, contract: ClassificationContract) -> dict[str, Any]:
    """Convert a model response to a source-backed and independently scored report.

    A quote demonstrates the model *cited* original text, not that its semantic
    judgement is infallible. More stringent semantic quality benchmarks and
    independent admission gates are required in M05 before any live use.
    """
    if not isinstance(contract, ClassificationContract):
        raise ClassificationContractError("invalid_contract")
    body = _decode(raw)
    if (body["contract_version"] != CLASSIFICATION_VERSION
            or body["source_hash"] != contract.source_hash):
        raise ClassificationContractError("stale_source")
    rows = body["classifications"]
    if not isinstance(rows, list) or len(rows) != len(contract.requirements):
        raise ClassificationContractError("incomplete_classifications")

    requirements = {item.requirement_id: item for item in contract.requirements}
    facts = {item["id"]: item["text"] for item in contract.candidate_facts}
    seen: set[str] = set()
    canonical = []
    weighted = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "requirement_id", "status", "candidate_evidence"
        }:
            raise ClassificationContractError("invalid_output_schema")
        rid = row["requirement_id"]
        status = row["status"]
        if not isinstance(rid, str) or rid not in requirements or rid in seen:
            raise ClassificationContractError("invalid_requirement_reference")
        seen.add(rid)
        if not isinstance(status, str) or status not in (
            "matched", "unverified", "mismatch"
        ):
            raise ClassificationContractError("invalid_output_schema")

        evidence = row["candidate_evidence"]
        if not isinstance(evidence, list) or len(evidence) > MAX_CANDIDATE_REFERENCES:
            raise ClassificationContractError("invalid_output_schema")
        if (status == "unverified" and evidence
                or status in ("matched", "mismatch") and not evidence):
            raise ClassificationContractError("unsupported_evidence")

        cited = []
        cited_ids: set[str] = set()
        for reference in evidence:
            if not isinstance(reference, dict) or set(reference) != {"id", "quote"}:
                raise ClassificationContractError("invalid_output_schema")
            fact_id = reference["id"]
            if (not isinstance(fact_id, str) or fact_id not in facts
                    or fact_id in cited_ids):
                raise ClassificationContractError("invalid_candidate_reference")
            cited_ids.add(fact_id)
            quote = reference["quote"]
            _check_quote(quote, facts[fact_id])
            cited.append({"id": fact_id, "quote": quote})

        spec = requirements[rid]
        if cited:
            requirement_tokens = _tokens(spec.text)
            supporting_tokens = frozenset().union(
                *(_tokens(reference["quote"]) for reference in cited)
            )
            if not requirement_tokens or not requirement_tokens & supporting_tokens:
                raise ClassificationContractError("unsupported_classification")

            evidence_text = " ".join(item["quote"] for item in cited)
            if status == "matched":
                # Numeric requirements cannot be substantiated by an unrelated
                # skill citation. Do not infer years/certificates from silence.
                if (not set(_NUMBER.findall(spec.text))
                        <= set(_NUMBER.findall(evidence_text))
                        or _NEGATION.search(evidence_text)):
                    raise ClassificationContractError("unsupported_classification")
            elif status == "mismatch":
                # Missing evidence is NEVER a proven mismatch. Conservative v1
                # allows explicit negative self-declarations only.
                if not _NEGATION.search(evidence_text):
                    raise ClassificationContractError("unsupported_classification")

        canonical.append({
            "requirement_id": rid,
            "requirement": spec.text,
            "source_id": spec.source_id,
            "importance": spec.importance,
            "weight": spec.weight,
            "status": status,
            "candidate_evidence": cited,
        })
        weighted.append(MatchRequirement(rid, spec.importance, spec.weight, status))

    if seen != requirements.keys():
        raise ClassificationContractError("incomplete_classifications")

    # The provider's order is never authoritative.
    by_id = {row["requirement_id"]: row for row in canonical}
    canonical = [by_id[item.requirement_id] for item in contract.requirements]
    weighted_by_id = {row.requirement_id: row for row in weighted}
    try:
        summary = calculate_match([
            weighted_by_id[item.requirement_id] for item in contract.requirements
        ])
    except MatchError:
        raise ClassificationContractError("invalid_classifications") from None

    return {
        "classification_version": CLASSIFICATION_VERSION,
        "source_hash": contract.source_hash,
        "resume_hash": contract.resume_hash,
        "vacancy_hash": contract.vacancy_hash,
        "summary": summary,
        "requirements": canonical,
        "presentation": "source_quotes_and_code_labels",
    }

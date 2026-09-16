"""AI-004 deterministic evidence coverage, independent of any provider.

This percentage describes supplied evidence, never a hiring probability or a
claim that an unrecorded skill is absent. Only validated requirements may enter.
"""
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Sequence

MATCH_VERSION = "weighted-evidence-v1"
FIXTURE_IDS = ("vacancy-match-ru-01", "vacancy-match-en-01")
MAX_REPORTS_PER_OWNER = 100
MAX_REQUIREMENTS = 64

class MatchError(ValueError):
    """Fixed public error codes; no user input or exception details."""

@dataclass(frozen=True, slots=True)
class MatchRequest:
    user_id: str = field(repr=False)
    fixture_id: str
    source_hash: str
    operation_key: str = field(repr=False)

@dataclass(frozen=True, slots=True)
class MatchRequirement:
    requirement_id: str
    importance: str
    weight: int
    status: str


def calculate_match(rows: Sequence[MatchRequirement]) -> dict[str, Any]:
    """Stable score with exact fractions; banker's rounding matches benchmark.

    `unverified` means insufficient evidence; `mismatch` is reserved for an
    explicit, evidenced conflict. Both remain visible and contribute no points.
    No partial credit or provider-authored weights/percentages are accepted.
    """
    if not isinstance(rows, Sequence) or not 1 <= len(rows) <= MAX_REQUIREMENTS:
        raise MatchError("invalid_classifications")
    identifiers = set()
    for row in rows:
        if (not isinstance(row, MatchRequirement) or not isinstance(row.requirement_id, str)
                or not row.requirement_id or row.requirement_id in identifiers
                or not isinstance(row.importance, str) or row.importance not in {"mandatory", "preferred"}
                or type(row.weight) is not int or not 1 <= row.weight <= 100
                or not isinstance(row.status, str) or row.status not in {"matched", "unverified", "mismatch"}):
            raise MatchError("invalid_classifications")
        identifiers.add(row.requirement_id)
    total = sum(row.weight for row in rows)
    matched = sum(row.weight for row in rows if row.status == "matched")
    unknown = sum(row.weight for row in rows if row.status == "unverified")
    missing_mandatory = sorted(row.requirement_id for row in rows
                              if row.importance == "mandatory" and row.status != "matched")
    score = round(Fraction(100 * matched, total))
    verdict = "strong" if not missing_mandatory and score >= 80 else "partial" if score >= 50 else "weak"
    return {
        "policy_version": MATCH_VERSION, "score_percent": score,
        "matched_weight": matched, "total_weight": total,
        "unverified_weight": unknown, "mismatch_weight": total - matched - unknown,
        "evidence_coverage_percent": round(Fraction(100 * (total - unknown), total)),
        "requirement_count": len(rows), "classified_count": len(rows),
        "mandatory_unresolved_ids": missing_mandatory, "verdict": verdict,
        "confidence_kind": "evidence_coverage_not_probability",
    }

"""AI004-M02: deterministic, non-AI prioritisation of bounded vacancy candidates.

This is a *cost-control queue*, not a relevance percentage or evidence of
qualification. Every candidate remains visible in one of three explicit sets:
shortlisted, deferred, or unscanned. Zero lexical overlap never means mismatch.

Callers must obtain the resume/version and vacancy snapshots through their
existing owner-qualified paths, then use AI004-M01 projections. This module
does not authenticate, fetch, persist, call a provider or grant legal admission.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from services.matching_input import VERSION as INPUT_VERSION

POLICY_VERSION = "ai004-prefilter-v1"
MAX_INPUT_ITEMS = 500
MAX_SCANNED = 200
MAX_SHORTLIST = 20

_RESUME_FIELDS = frozenset(
    ("resume.role", "resume.experience", "resume.achievements",
     "resume.skills", "resume.education")
)
_VACANCY_FIELDS = frozenset(
    ("title", "company", "description", "requirements", "work_format",
     "employment_code", "experience_code", "location", "currency",
     "salary_from", "salary_to")
)
_TOKEN = re.compile(r"(?u)[^\W_]+(?:[+#.][^\W_]*)*")
_STOP = frozenset((
    "and", "the", "with", "for", "you", "your", "are", "required",
    "requirements", "experience", "skills", "knowledge", "work", "job",
    "и", "или", "для", "при", "это", "как", "все", "всех",
    "опыт", "работа", "работы", "знание", "знания",
    "требования", "обязанности", "навыки",
))


class PrefilterError(ValueError):
    """Fixed public error code; never include source content."""


@dataclass(frozen=True, slots=True)
class VacancyCandidate:
    """Stable, unique key from a trusted owner-qualified source + M01 projection."""

    stable_key: str
    projection: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PrefilterResult:
    shortlisted: tuple[str, ...]
    deferred: tuple[str, ...]
    unscanned: tuple[str, ...]
    total_items: int
    scanned_items: int
    policy_version: str = POLICY_VERSION

    @property
    def scope_limited(self) -> bool:
        return bool(self.deferred or self.unscanned)


def _verify_projection(value: Any, *, kind: str) -> None:
    """Detect invalid/mutated M01 projections; not a substitute for ownership."""
    payload_key = "facts" if kind == "resume_version" else "fields"
    if not isinstance(value, Mapping) or set(value) != {
        "version", "kind", payload_key, "content_hash"
    }:
        raise PrefilterError("invalid_projection")
    if value["version"] != INPUT_VERSION or value["kind"] != kind:
        raise PrefilterError("invalid_projection")
    fingerprint = value["content_hash"]
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise PrefilterError("invalid_projection")
    payload = value[payload_key]
    if kind == "resume_version":
        if not isinstance(payload, list) or not 1 <= len(payload) <= 5:
            raise PrefilterError("invalid_projection")
        keys: set[str] = set()
        for fact in payload:
            if (not isinstance(fact, dict) or set(fact) != {"id", "text"}
                    or not isinstance(fact["id"], str)
                    or fact["id"] not in _RESUME_FIELDS
                    or fact["id"] in keys
                    or not isinstance(fact["text"], str)
                    or not 0 < len(fact["text"]) <= 8000):
                raise PrefilterError("invalid_projection")
            keys.add(fact["id"])
    else:
        if not isinstance(payload, dict) or set(payload) != _VACANCY_FIELDS:
            raise PrefilterError("invalid_projection")
        if (not isinstance(payload["title"], str)
                or not payload["title"].strip()):
            raise PrefilterError("invalid_projection")
        for name in _VACANCY_FIELDS - {"salary_from", "salary_to"}:
            if not isinstance(payload[name], str) or len(payload[name]) > 32000:
                raise PrefilterError("invalid_projection")
        for name in ("salary_from", "salary_to"):
            number = payload[name]
            if number is not None and (type(number) not in (int, float)
                                       or not 0 <= number <= 1e12):
                raise PrefilterError("invalid_projection")
    try:
        canonical = json.dumps(
            {key: value[key] for key in ("version", "kind", payload_key)},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
    except (ValueError, TypeError):
        raise PrefilterError("invalid_projection") from None
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != fingerprint:
        raise PrefilterError("invalid_projection")


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token for token in (word.casefold() for word in _TOKEN.findall(text))
        if len(token) >= 2 and token not in _STOP
    )


def _priority(
    fields: Mapping[str, Any], role: frozenset[str],
    skills: frozenset[str], facts: frozenset[str],
) -> tuple[int, int, int, int]:
    """Lexical *screening* signals only; never expose as a match score."""
    title = _tokens(fields["title"])
    requirements = _tokens(fields["requirements"] or fields["description"])
    return (
        min(len(role & title), 10),
        min(len(skills & requirements), 10),
        min(len(facts & requirements), 10),
        min(len(facts & title), 10),
    )


def prefilter_vacancies(
    resume: Mapping[str, Any],
    candidates: Sequence[VacancyCandidate],
    *,
    shortlist_limit: int = MAX_SHORTLIST,
    scan_limit: int = MAX_SCANNED,
) -> PrefilterResult:
    """Prioritise first scan_limit items; retain every unassessed item by key.

    Input order comes from the existing SEARCH/JOB snapshot. Stable input order
    breaks all lexical ties, including missing requirements or cross-language
    wording with zero overlap. Shortlisted means *candidate for review*, not
    evaluated or matched. M05 performs cache lookup and budget admission later.
    """
    _verify_projection(resume, kind="resume_version")
    if (type(shortlist_limit) is not int or type(scan_limit) is not int
            or not 1 <= shortlist_limit <= MAX_SHORTLIST
            or not shortlist_limit <= scan_limit <= MAX_SCANNED
            or not isinstance(candidates, Sequence)
            or isinstance(candidates, (str, bytes))
            or len(candidates) > MAX_INPUT_ITEMS):
        raise PrefilterError("invalid_limits")
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, VacancyCandidate):
            raise PrefilterError("invalid_candidate")
        key = candidate.stable_key
        if (not isinstance(key, str) or not 0 < len(key) <= 256
                or key != key.strip()
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in key)
                or key in seen):
            raise PrefilterError("invalid_candidate")
        seen.add(key)

    # Validate only the bounded scoring window. Later windows must be called
    # separately with the same source/ownership guarantees.
    scanned = candidates[:scan_limit]
    for candidate in scanned:
        _verify_projection(candidate.projection, kind="saved_vacancy")
    facts_by_id = {row["id"]: _tokens(row["text"]) for row in resume["facts"]}
    role = facts_by_id.get("resume.role", frozenset())
    skills = facts_by_id.get("resume.skills", frozenset())
    all_facts = frozenset().union(*facts_by_id.values())
    priorities = [
        (_priority(candidate.projection["fields"], role, skills, all_facts), index, candidate.stable_key)
        for index, candidate in enumerate(scanned)
    ]
    priorities.sort(key=lambda item: (tuple(-value for value in item[0]), item[1]))
    ordered = tuple(item[2] for item in priorities)
    return PrefilterResult(
        shortlisted=ordered[:shortlist_limit],
        deferred=ordered[shortlist_limit:],
        unscanned=tuple(candidate.stable_key for candidate in candidates[scan_limit:]),
        total_items=len(candidates),
        scanned_items=len(scanned),
    )

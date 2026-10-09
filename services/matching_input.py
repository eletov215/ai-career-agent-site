"""AI004-M01: bounded, provider-free projections of immutable source snapshots.

The caller MUST fetch a ResumeVersion through an owner-qualified draft lookup and
a saved vacancy through SavedVacancyService.get(user_id, saved_id).  This pure
module deliberately has no database, AI or web dependency.  It is not an AI
admission API: real personal data must never be passed to a provider while the
legal gate is closed.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

VERSION = "ai004-input-v1"
_RESUME_KEYS = ("role", "experience", "achievements", "skills", "education")
_VACANCY_KEYS = ("title", "company", "description", "requirements",
                 "work_format", "employment_code", "experience_code",
                 "location", "currency", "salary_from", "salary_to")
_MAX_RESUME_FIELD = 8000
_MAX_VACANCY_FIELD = 32000


class MatchInputError(ValueError):
    """A fixed, safe failure reason without submitted text."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > limit or any(
        ord(ch) < 32 and ch not in "\n\t\r" for ch in value
    ):
        raise MatchInputError("invalid_source")
    return value.strip()


def project_resume_version(version: Mapping[str, Any]) -> dict[str, Any]:
    """Project a previously owner-verified, immutable PROF-003 version.

    A draft ID or PDF is not proof of ownership. Route/repository integration
    MUST obtain the version with an owner-qualified query before this call.
    """
    if not isinstance(version, Mapping):
        raise MatchInputError("invalid_source")
    snapshot = version.get("snapshot")
    if snapshot is None and isinstance(version.get("snapshot_json"), str):
        try:
            snapshot = json.loads(version["snapshot_json"])
        except (ValueError, TypeError):
            raise MatchInputError("invalid_source") from None
    if not isinstance(snapshot, dict) or snapshot.get("schemaVersion") != 1:
        raise MatchInputError("invalid_source")
    answers = snapshot.get("answers")
    if not isinstance(answers, dict):
        raise MatchInputError("invalid_source")
    facts = []
    for name in _RESUME_KEYS:
        value = _text(answers.get(name), _MAX_RESUME_FIELD)
        if value:
            facts.append({"id": "resume." + name, "text": value})
    if not facts:
        raise MatchInputError("insufficient_source")
    data = {"version": VERSION, "kind": "resume_version", "facts": facts}
    return {**data, "content_hash": _hash(data)}


def project_saved_vacancy(saved: Mapping[str, Any]) -> dict[str, Any]:
    """Project a previously owner-verified JOB-001 immutable vacancy snapshot.

    Personal notes, source URLs and provider raw JSON never leave this boundary.
    """
    if not isinstance(saved, Mapping) or not isinstance(saved.get("snapshot"), dict):
        raise MatchInputError("invalid_source")
    source = saved["snapshot"]
    if source.get("snapshot_version") != "saved-vacancy-v1":
        # Version is validated again by the owner-qualified repository reader.
        raise MatchInputError("invalid_source")
    fields = {}
    for key in _VACANCY_KEYS:
        value = source.get(key)
        if key in ("salary_from", "salary_to"):
            if value is not None and (type(value) not in (int, float)
                                      or not math.isfinite(value) or value < 0 or value > 1e12):
                raise MatchInputError("invalid_source")
            fields[key] = value
        else:
            fields[key] = _text(value, _MAX_VACANCY_FIELD)
    if not fields["title"]:
        raise MatchInputError("insufficient_source")
    data = {"version": VERSION, "kind": "saved_vacancy", "fields": fields}
    return {**data, "content_hash": _hash(data)}

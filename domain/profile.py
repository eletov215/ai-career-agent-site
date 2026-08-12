"""Immutable structured career-profile records for PROF-001."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CareerProfileRecord:
    """Current owner-scoped profile state detached from SQLAlchemy."""

    id: str
    user_id: str
    schema_version: int
    version: int
    headline: str | None
    summary: str | None
    contacts_json: str
    goals_json: str
    geography_json: str
    salary_json: str
    skills_json: str
    employment_json: str
    achievements_json: str
    education_json: str
    languages_json: str
    content_hash: str
    completion_percent: int
    confirmed_at: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class CareerProfileVersionRecord:
    """One immutable user-confirmed profile snapshot."""

    id: str
    profile_id: str
    schema_version: int
    version: int
    snapshot_json: str
    content_hash: str
    changed_sections_json: str
    created_at: int

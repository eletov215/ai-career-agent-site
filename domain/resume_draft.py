"""Immutable domain records for PROF-003 server-side resume drafts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResumeDraftRecord:
    """Current owner-scoped resume draft state detached from SQLAlchemy."""

    id: str
    user_id: str
    schema_version: int
    revision: int
    title: str
    state_json: str
    content_hash: str
    completion_percent: int
    profile_version: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class ResumeVersionRecord:
    """One immutable resume snapshot created by checkpoint/export/restore."""

    id: str
    draft_id: str
    schema_version: int
    version: int
    draft_revision: int
    snapshot_json: str
    content_hash: str
    reason: str
    restored_from_version: int | None
    created_at: int


@dataclass(frozen=True, slots=True)
class ResumeAssetRecord:
    """One owner-scoped durable image object used by a draft or version."""

    id: str
    draft_id: str
    user_id: str
    kind: str
    content_type: str
    byte_size: int
    sha256: str
    data: bytes
    created_at: int


@dataclass(frozen=True, slots=True)
class ResumeExportRecord:
    """Metadata for one browser-generated PDF export."""

    id: str
    draft_id: str
    version_id: str
    version: int
    page_count: int
    byte_size: int
    pdf_sha256: str
    file_name: str
    created_at: int

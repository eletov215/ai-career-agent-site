"""Immutable resume-import review records for PROF-002."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResumeImportSignal:
    """One explainable extraction suggestion."""

    path: str
    confidence: str
    source_excerpt: str


@dataclass(frozen=True, slots=True)
class ResumeImportConflict:
    """Difference between a confirmed profile scalar and PDF suggestion."""

    path: str
    current_value: str
    suggested_value: str


@dataclass(frozen=True, slots=True)
class ResumeImportProposal:
    """Ephemeral editable proposal; it is not persisted as profile facts."""

    filename: str
    page_count: int
    character_count: int
    payload: dict[str, Any]
    extracted_payload: dict[str, Any]
    signals: tuple[ResumeImportSignal, ...]
    section_confidence: dict[str, str]
    warnings: tuple[str, ...]
    conflicts: tuple[ResumeImportConflict, ...]
    detected_sections: tuple[str, ...]

    @property
    def overall_confidence(self) -> str:
        levels = set(self.section_confidence.values())
        if "low" in levels:
            return "low"
        if "medium" in levels:
            return "medium"
        return "high" if levels else "low"

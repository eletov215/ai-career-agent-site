"""Provider-independent vacancy contract for SEARCH-001.

The application keeps provider display labels for transparency, but all code
that filters or presents a vacancy uses explicit canonical codes.  Unknown
values stay unknown; the normalizer must not silently guess an on-site job,
full employment, or an experience bracket when a provider does not supply
reliable evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


CONTRACT_VERSION = 1


class WorkFormat(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FIELD = "field"
    FLY_IN_FLY_OUT = "fly_in_fly_out"
    UNKNOWN = "unknown"


class EmploymentCode(StrEnum):
    FULL = "full"
    PART = "part"
    PROJECT = "project"
    TEMPORARY = "temporary"
    PROBATION = "probation"
    VOLUNTEER = "volunteer"
    SHIFT = "shift"
    SIDE_JOB = "side_job"
    UNKNOWN = "unknown"


class ExperienceCode(StrEnum):
    NO_EXPERIENCE = "no_experience"
    BETWEEN_1_AND_3 = "between_1_and_3"
    BETWEEN_3_AND_6 = "between_3_and_6"
    MORE_THAN_6 = "more_than_6"
    UNKNOWN = "unknown"


WORK_FORMAT_VALUES = frozenset(item.value for item in WorkFormat)
EMPLOYMENT_VALUES = frozenset(item.value for item in EmploymentCode)
EXPERIENCE_VALUES = frozenset(item.value for item in ExperienceCode)


def canonical_code(value: Any, allowed: frozenset[str], *, default: str = "unknown") -> str:
    """Return a valid lowercase code without inventing a fallback meaning."""

    candidate = str(value or "").strip().casefold()
    return candidate if candidate in allowed else default


@dataclass(frozen=True, slots=True)
class NormalizedVacancy:
    """Typed provider-to-application vacancy boundary.

    ``schedule``, ``employment`` and ``experience`` are provider display
    labels retained for the UI and diagnostics.  Their canonical counterparts
    are the only values used for new filter decisions.
    """

    external_id: str
    source: str
    source_title: str
    title: str
    company: str
    salary_from: float | None
    salary_to: float | None
    currency: str
    location: str
    work_format: str
    employment_code: str
    experience_code: str
    schedule: str
    employment: str
    experience: str
    description: str
    requirements: str
    published_at: str | None
    url: str
    source_status: str = "active"
    source_modified_at: str | None = None
    closed_reason: str | None = None
    closed_at: int | None = None
    contract_version: int = CONTRACT_VERSION

    @property
    def remote(self) -> bool:
        """Legacy compatibility flag; hybrid remains explicitly hybrid."""

        return self.work_format == WorkFormat.REMOTE.value

    def as_mapping(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["remote"] = self.remote
        return payload

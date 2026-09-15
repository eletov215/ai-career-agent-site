"""AI-002 typed boundary; only pinned synthetic inputs are supported."""
from dataclasses import dataclass, field
from typing import Any

ANALYSIS_VERSION = "synthetic-analysis-v1"
FIXTURE_IDS = ("resume-analysis-ru-01", "resume-analysis-en-01")
MAX_REPORTS_PER_OWNER = 100

class AnalysisError(ValueError):
    """A safe, fixed error code; never a resume, credential or provider body."""

@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    user_id: str = field(repr=False)
    idempotency_key: str = field(repr=False)
    fixture_id: str
    expected_source_hash: str

@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    status: str
    reason: str
    report: dict[str, Any] | None = field(default=None, repr=False)

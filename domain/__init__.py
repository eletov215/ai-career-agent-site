"""Domain-facing records detached from SQLAlchemy sessions."""

from .auth import (
    AuthActionResult,
    AuthenticatedSession,
    AuthSessionRecord,
    AuthTokenRecord,
    AuthUserRecord,
)
from .profile import CareerProfileRecord, CareerProfileVersionRecord
from .vacancy_contract import (
    CONTRACT_VERSION,
    EMPLOYMENT_VALUES,
    EXPERIENCE_VALUES,
    WORK_FORMAT_VALUES,
    EmploymentCode,
    ExperienceCode,
    NormalizedVacancy,
    WorkFormat,
)
from .entities import (
    OAuthConnectionRecord,
    SearchSnapshotCandidateRecord,
    SearchSnapshotItemRecord,
    SearchSnapshotRecord,
    SearchSnapshotSourceRecord,
    SourceRecord,
    SyncCheckpointRecord,
    SyncRunRecord,
    SyncWorkerRecord,
    UserRecord,
    VacancyRecord,
)
__all__ = [
    "AuthActionResult",
    "AuthenticatedSession",
    "AuthSessionRecord",
    "AuthTokenRecord",
    "AuthUserRecord",
    "CareerProfileRecord",
    "CareerProfileVersionRecord",
    "CONTRACT_VERSION",
    "EMPLOYMENT_VALUES",
    "EXPERIENCE_VALUES",
    "WORK_FORMAT_VALUES",
    "EmploymentCode",
    "ExperienceCode",
    "NormalizedVacancy",
    "WorkFormat",
    "OAuthConnectionRecord",
    "SearchSnapshotCandidateRecord",
    "SearchSnapshotItemRecord",
    "SearchSnapshotRecord",
    "SearchSnapshotSourceRecord",
    "SourceRecord",
    "SyncCheckpointRecord",
    "SyncRunRecord",
    "SyncWorkerRecord",
    "UserRecord",
    "VacancyRecord",
    "ResumeImportConflict",
    "ResumeImportProposal",
    "ResumeImportSignal",
]

from .resume_import import (
    ResumeImportConflict,
    ResumeImportProposal,
    ResumeImportSignal,
)

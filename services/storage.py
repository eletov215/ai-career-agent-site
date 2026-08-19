"""Application storage service bundle.

Flask routes depend on this bundle rather than constructing repositories or
importing ORM models.  CLI jobs and future account/profile services can reuse
the same repository contracts against SQLite tests or production PostgreSQL.
"""

from __future__ import annotations

from dataclasses import dataclass

from database import DatabaseRuntime
from repositories import (
    AuthRepository,
    CareerProfileRepository,
    OAuthConnectionRepository,
    PrivacyRepository,
    ResumeDraftRepository,
    SearchSnapshotRepository,
    SyncCheckpointRepository,
    SyncRunRepository,
    SyncWorkerRepository,
    UserRepository,
)
from services.vacancy_store import VacancyStore


@dataclass(frozen=True, slots=True)
class StorageServices:
    """Repository-backed persistence entry points for application services."""

    auth: AuthRepository
    profiles: CareerProfileRepository
    resume_drafts: ResumeDraftRepository
    users: UserRepository
    oauth_connections: OAuthConnectionRepository
    privacy: PrivacyRepository
    search_snapshots: SearchSnapshotRepository
    sync_checkpoints: SyncCheckpointRepository
    sync_runs: SyncRunRepository
    sync_workers: SyncWorkerRepository
    vacancies: VacancyStore

    @classmethod
    def from_database(cls, database: DatabaseRuntime) -> "StorageServices":
        return cls(
            auth=AuthRepository(database),
            profiles=CareerProfileRepository(database),
            resume_drafts=ResumeDraftRepository(database),
            users=UserRepository(database),
            oauth_connections=OAuthConnectionRepository(database),
            privacy=PrivacyRepository(database),
            search_snapshots=SearchSnapshotRepository(database),
            sync_checkpoints=SyncCheckpointRepository(database),
            sync_runs=SyncRunRepository(database),
            sync_workers=SyncWorkerRepository(database),
            vacancies=VacancyStore(database),
        )

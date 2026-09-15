"""SQLAlchemy persistence models for the current application schema."""

from .accounts import HeadHunterAccount, SuperJobAccount
from .auth import AuthSession, AuthToken
from .base import Base
from .resume_analysis import ResumeAnalysisReport, ResumeAnalysisDecision, ResumeAnalysisReviewEvent
from .oauth_connection import OAuthConnection
from .profile import CareerProfile, CareerProfileVersion
from .privacy import PrivacyAuditEvent
from .resume import ResumeAsset, ResumeDraft, ResumeExport, ResumeVersion
from .source_health import SourceHealthState
from .search_snapshot import (
    SearchSnapshot,
    SearchSnapshotCandidate,
    SearchSnapshotItem,
    SearchSnapshotSource,
)
from .sync_checkpoint import SyncCheckpoint
from .sync_run import SyncRun
from .sync_worker import SyncWorker
from .user import User
from .vacancy import Vacancy, VacancySourceRecord

__all__ = [
    "Base",
    "AuthSession",
    "AuthToken",
    "HeadHunterAccount",
    "OAuthConnection",
    "CareerProfile",
    "CareerProfileVersion",
    "PrivacyAuditEvent",
    "ResumeAsset",
    "ResumeDraft",
    "ResumeExport",
    "ResumeVersion",
    "SuperJobAccount",
    "SyncCheckpoint",
    "SyncRun",
    "SyncWorker",
    "SourceHealthState",
    "SearchSnapshot",
    "SearchSnapshotCandidate",
    "SearchSnapshotItem",
    "SearchSnapshotSource",
    "User",
    "Vacancy",
    "VacancySourceRecord",
]

# AI-001 metadata registration (additive migration 0015).
from .ai import (AIRuntimePolicy, AIUsageEvent, AIBudgetBucket, AIRequestLease, AIProviderState, AIPlanEntitlement, AIUserPlan)

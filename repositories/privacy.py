"""Repository boundary for PRIV-001 export, deletion, and retention cleanup."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, or_, select, text
from models.ai import AIUsageEvent, AIUserPlan, AIBudgetBucket
from models.consent import AIConsent
from models.resume_analysis import ResumeAnalysisReport, ResumeAnalysisDecision, ResumeAnalysisReviewEvent
from repositories.resume_analysis import report_view
from models.vacancy_match import VacancyMatchReport, VacancyMatchSeries
from models.saved_vacancy import SavedVacancy, SavedVacancySource
from models.application_tracker import SavedVacancyTracker, SavedVacancyTrackerEvent
from models.reminder import NotificationPreference, SavedVacancyReminder
from repositories.reminders import preference_view, reminder_view
from repositories.application_trackers import tracker_view, event_view
from models.cover_letter import CoverLetter, CoverLetterVersion, CoverLetterProposal
from repositories.cover_letters import CoverLetterRepository
from domain.cover_letter import LetterError
from repositories.saved_vacancies import saved_view, source_view
from domain.saved_vacancy import MAX_SAVED, MAX_SOURCES, SavedVacancyError
from repositories.vacancy_match import match_view
from models.resume_interview import ResumeInterviewSession, ResumeInterviewEvent
from repositories.resume_interview import interview_snapshot
from repositories.ai import public_usage

from models import (
    AuthSession,
    AuthToken,
    CareerProfile,
    CareerProfileVersion,
    HeadHunterAccount,
    OAuthConnection,
    PrivacyAuditEvent,
    ResumeAsset,
    ResumeDraft,
    ResumeExport,
    ResumeVersion,
    SuperJobAccount,
    User,
)

from .base import RepositoryBase


@dataclass(frozen=True, slots=True)
class PrivacyAssetExport:
    id: str
    draft_id: str
    kind: str
    content_type: str
    byte_size: int
    sha256: str
    data: bytes
    created_at: int


def _json_value(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw


def _json_object(raw: str | None) -> dict[str, Any]:
    value = _json_value(raw, {})
    return value if isinstance(value, dict) else {}


def _raw_state_references_asset(raw: str | None, asset_id: str) -> bool:
    if not raw or asset_id not in raw:
        return False
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        # Conservative on malformed historical state: if the UUID appears at all, keep it.
        return True

    def walk(item: Any) -> bool:
        if isinstance(item, dict):
            return any(walk(value) for value in item.values())
        if isinstance(item, list):
            return any(walk(value) for value in item)
        return str(item) == asset_id if item is not None else False

    return walk(value)


class PrivacySnapshotConflictError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PrivacyRepository(RepositoryBase):
    """Read sanitized owner data and perform complete account deletion."""

    @staticmethod
    def _audit_row(event_type: str, counts: dict[str, int], *, now: int) -> PrivacyAuditEvent:
        safe_counts = {
            str(key)[:64]: max(0, int(value))
            for key, value in sorted(counts.items())
        }
        return PrivacyAuditEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            counts_json=json.dumps(safe_counts, sort_keys=True, separators=(",", ":")),
            created_at=now,
        )

    @staticmethod
    def _count(session, model, *conditions) -> int:  # noqa: ANN001
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(session.scalar(statement) or 0)

    def export_snapshot(
        self,
        user_id: str,
        *,
        expected_password_hash: str,
    ) -> tuple[dict[str, Any], list[PrivacyAssetExport]] | None:
        """Return one consistent, owner-locked export snapshot."""

        with self.session() as session:
            if self.engine.dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            user_stmt = select(User).where(User.id == str(user_id))
            if self.engine.dialect.name == "postgresql":
                user_stmt = user_stmt.with_for_update()
            user = session.scalar(user_stmt)
            if user is None:
                return None
            if not expected_password_hash or user.password_hash != expected_password_hash:
                raise PrivacySnapshotConflictError("password_changed")

            sessions = session.scalars(
                select(AuthSession)
                .where(AuthSession.user_id == user.id)
                .order_by(AuthSession.created_at.asc())
            ).all()
            tokens = session.scalars(
                select(AuthToken)
                .where(AuthToken.user_id == user.id)
                .order_by(AuthToken.created_at.asc())
            ).all()
            oauth_rows = session.scalars(
                select(OAuthConnection)
                .where(OAuthConnection.user_id == user.id)
                .order_by(OAuthConnection.provider.asc(), OAuthConnection.created_at.asc())
            ).all()
            profile = session.scalar(
                select(CareerProfile).where(CareerProfile.user_id == user.id)
            )
            profile_versions = []
            if profile is not None:
                profile_versions = session.scalars(
                    select(CareerProfileVersion)
                    .where(CareerProfileVersion.profile_id == profile.id)
                    .order_by(CareerProfileVersion.version.asc())
                ).all()

            drafts = session.scalars(
                select(ResumeDraft)
                .where(ResumeDraft.user_id == user.id)
                .order_by(ResumeDraft.created_at.asc())
            ).all()
            draft_ids = [row.id for row in drafts]
            # Corrupt owner/draft relationships fail closed instead of exporting an ambiguous asset.
            if draft_ids:
                mismatch_owned = self._count(
                    session,
                    ResumeAsset,
                    ResumeAsset.user_id == user.id,
                    ResumeAsset.draft_id.not_in(draft_ids),
                )
                mismatch_draft = self._count(
                    session,
                    ResumeAsset,
                    ResumeAsset.draft_id.in_(draft_ids),
                    ResumeAsset.user_id != user.id,
                )
            else:
                mismatch_owned = self._count(
                    session, ResumeAsset, ResumeAsset.user_id == user.id
                )
                mismatch_draft = 0
            if mismatch_owned or mismatch_draft:
                raise PrivacySnapshotConflictError("asset_owner_mismatch")
            versions = []
            exports = []
            asset_rows = []
            if draft_ids:
                versions = session.scalars(
                    select(ResumeVersion)
                    .where(ResumeVersion.draft_id.in_(draft_ids))
                    .order_by(ResumeVersion.draft_id.asc(), ResumeVersion.version.asc())
                ).all()
                exports = session.scalars(
                    select(ResumeExport)
                    .where(ResumeExport.draft_id.in_(draft_ids))
                    .order_by(ResumeExport.draft_id.asc(), ResumeExport.created_at.asc())
                ).all()
                asset_rows = session.scalars(
                    select(ResumeAsset)
                    .where(
                        ResumeAsset.user_id == user.id,
                        ResumeAsset.draft_id.in_(draft_ids),
                    )
                    .order_by(ResumeAsset.draft_id.asc(), ResumeAsset.created_at.asc())
                ).all()

            ai_rows = session.scalars(select(AIUsageEvent).where(AIUsageEvent.user_id == user.id)
                                      .order_by(AIUsageEvent.created_at.asc()).limit(5001)).all()
            if len(ai_rows) > 5000:
                raise PrivacySnapshotConflictError("ai_export_limit")
            consent_rows = session.scalars(
                select(AIConsent).where(AIConsent.user_id == user.id)
                .order_by(AIConsent.created_at.asc(), AIConsent.cycle.asc(), AIConsent.id.asc())
                .limit(501)
            ).all()
            if len(consent_rows) > 500:
                raise PrivacySnapshotConflictError("consent_export_limit")
            analysis_rows = session.scalars(select(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user.id)
                .order_by(ResumeAnalysisReport.created_at, ResumeAnalysisReport.id).limit(101)).all()
            if len(analysis_rows) > 100:
                raise PrivacySnapshotConflictError("analysis_export_limit")
            analysis_export = []
            for row in analysis_rows:
                decisions = session.scalars(select(ResumeAnalysisDecision).where(ResumeAnalysisDecision.report_id == row.id)).all()
                review_events = session.scalars(select(ResumeAnalysisReviewEvent).where(ResumeAnalysisReviewEvent.report_id == row.id)
                    .order_by(ResumeAnalysisReviewEvent.created_at, ResumeAnalysisReviewEvent.revision)).all()
                analysis_export.append(report_view(row, decisions, review_events))
            interview_rows = session.scalars(select(ResumeInterviewSession).where(
                ResumeInterviewSession.user_id == user.id
            ).order_by(ResumeInterviewSession.created_at, ResumeInterviewSession.id).limit(51)).all()
            if len(interview_rows) > 50:
                raise PrivacySnapshotConflictError('interview_export_limit')
            interview_export = []
            for row in interview_rows:
                if row.draft_id not in draft_ids:
                    raise PrivacySnapshotConflictError('interview_owner_mismatch')
                events = session.scalars(select(ResumeInterviewEvent).where(
                    ResumeInterviewEvent.session_id == row.id
                ).order_by(ResumeInterviewEvent.revision).limit(61)).all()
                if len(events) > 60:
                    raise PrivacySnapshotConflictError('interview_export_limit')
                interview_export.append(interview_snapshot(row, events))
            match_rows = session.scalars(select(VacancyMatchReport).where(
                VacancyMatchReport.user_id == user.id
            ).order_by(VacancyMatchReport.created_at, VacancyMatchReport.id).limit(101)).all()
            if len(match_rows) > 100:
                raise PrivacySnapshotConflictError('match_export_limit')
            match_series = session.scalars(select(VacancyMatchSeries).where(
                VacancyMatchSeries.user_id == user.id
            ).order_by(VacancyMatchSeries.fixture_id).limit(3)).all()
            if len(match_series) > 2:
                raise PrivacySnapshotConflictError('match_series_export_limit')
            saved_rows = session.scalars(select(SavedVacancy).where(SavedVacancy.user_id == user.id)
                .order_by(SavedVacancy.created_at, SavedVacancy.id).limit(MAX_SAVED+1)).all()
            saved_sources = session.scalars(select(SavedVacancySource).where(SavedVacancySource.user_id == user.id)
                .order_by(SavedVacancySource.saved_vacancy_id, SavedVacancySource.id).limit(MAX_SAVED*MAX_SOURCES+1)).all()
            if len(saved_rows) > MAX_SAVED or len(saved_sources) > MAX_SAVED*MAX_SOURCES:
                raise PrivacySnapshotConflictError('saved_vacancy_export_limit')
            saved_ids = {row.id for row in saved_rows}
            if any(source.saved_vacancy_id not in saved_ids for source in saved_sources):
                raise PrivacySnapshotConflictError('saved_vacancy_owner_mismatch')
            tracker_rows = session.scalars(select(SavedVacancyTracker).where(
                SavedVacancyTracker.user_id == user.id).order_by(
                SavedVacancyTracker.created_at, SavedVacancyTracker.saved_vacancy_id).limit(MAX_SAVED+1)).all()
            tracker_events = session.scalars(select(SavedVacancyTrackerEvent).where(
                SavedVacancyTrackerEvent.user_id == user.id).order_by(
                SavedVacancyTrackerEvent.saved_vacancy_id,
                SavedVacancyTrackerEvent.event_revision).limit(MAX_SAVED*100+1)).all()
            reminder_preference = session.get(NotificationPreference, user.id)
            reminder_rows = session.scalars(select(SavedVacancyReminder).where(
                SavedVacancyReminder.user_id == user.id).order_by(
                SavedVacancyReminder.due_date, SavedVacancyReminder.id).limit(MAX_SAVED+1)).all()
            if len(reminder_rows) > MAX_SAVED or any(row.saved_vacancy_id not in saved_ids for row in reminder_rows):
                raise PrivacySnapshotConflictError('reminder_owner_mismatch')
            tracker_ids = {row.saved_vacancy_id for row in tracker_rows}
            if (len(tracker_rows) > MAX_SAVED or len(tracker_events) > MAX_SAVED*100
                    or not tracker_ids <= saved_ids
                    or any(event.saved_vacancy_id not in tracker_ids for event in tracker_events)):
                raise PrivacySnapshotConflictError('application_tracker_owner_mismatch')
            try:
                saved_exports = [saved_view(row) for row in saved_rows]
            except SavedVacancyError:
                raise PrivacySnapshotConflictError('saved_vacancy_integrity') from None
            try:
                letter_export = CoverLetterRepository.export_in_session(session, user.id)
                if any(row['saved_vacancy_id'] not in saved_ids for row in letter_export['cover_letters']):
                    raise LetterError('storage_integrity')
            except LetterError:
                raise PrivacySnapshotConflictError('cover_letter_integrity') from None
            snapshot: dict[str, Any] = {
                **letter_export,
                "saved_vacancies": saved_exports,
                "saved_vacancy_sources": [source_view(row) for row in saved_sources],
                "notification_preference": preference_view(reminder_preference),
                "saved_vacancy_reminders": [reminder_view(row) for row in reminder_rows],
                "saved_vacancy_trackers": [tracker_view(row) | {'saved_vacancy_id': row.saved_vacancy_id}
                                             for row in tracker_rows],
                "saved_vacancy_tracker_events": [event_view(row) for row in tracker_events],
                "vacancy_matches": [match_view(row) for row in match_rows],
                "vacancy_match_series": [{"fixture_id": row.fixture_id, "last_version": row.last_version}
                                         for row in match_series],
                "resume_interviews": interview_export,
                "resume_analyses": analysis_export,
                "ai_usage": [public_usage(row) for row in ai_rows],
                "ai_consents": [
                    {
                        "id": row.id,
                        "consent_type": row.consent_type,
                        "scope": row.scope,
                        "policy_version": row.policy_version,
                        "policy_hash": row.policy_hash,
                        "provider": row.provider,
                        "purpose": row.purpose,
                        "status": row.status,
                        "cycle": row.cycle,
                        "revision": row.revision,
                        "accepted_at": row.accepted_at,
                        "withdrawn_at": row.withdrawn_at,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                    for row in consent_rows
                ],
                "schema_version": 1,
                "account": {
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "status": user.status,
                    "email_verified_at": user.email_verified_at,
                    "password_changed_at": user.password_changed_at,
                    "last_login_at": user.last_login_at,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                },
                "authentication": {
                    "sessions": [
                        {
                            "id": row.id,
                            "created_at": row.created_at,
                            "last_seen_at": row.last_seen_at,
                            "expires_at": row.expires_at,
                            "revoked_at": row.revoked_at,
                            "revoke_reason": row.revoke_reason,
                        }
                        for row in sessions
                    ],
                    "one_time_tokens": [
                        {
                            "id": row.id,
                            "purpose": row.purpose,
                            "created_at": row.created_at,
                            "expires_at": row.expires_at,
                            "consumed_at": row.consumed_at,
                            "consumed_reason": row.consumed_reason,
                        }
                        for row in tokens
                    ],
                },
                "oauth_connections": [
                    {
                        "id": row.id,
                        "provider": row.provider,
                        "external_user_id": row.external_user_id,
                        "display_name": row.display_name,
                        "first_name": row.first_name,
                        "last_name": row.last_name,
                        "email": row.email,
                        "expires_at": row.expires_at,
                        "profile": _json_object(row.profile_json),
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                    for row in oauth_rows
                ],
                "career_profile": None,
                "career_profile_versions": [],
                "resume_drafts": [
                    {
                        "id": row.id,
                        "schema_version": row.schema_version,
                        "revision": row.revision,
                        "title": row.title,
                        "state": _json_value(row.state_json, {}),
                        "content_hash": row.content_hash,
                        "completion_percent": row.completion_percent,
                        "profile_version": row.profile_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                    for row in drafts
                ],
                "resume_versions": [
                    {
                        "id": row.id,
                        "draft_id": row.draft_id,
                        "schema_version": row.schema_version,
                        "version": row.version,
                        "draft_revision": row.draft_revision,
                        "snapshot": _json_value(row.snapshot_json, {}),
                        "content_hash": row.content_hash,
                        "reason": row.reason,
                        "restored_from_version": row.restored_from_version,
                        "created_at": row.created_at,
                    }
                    for row in versions
                ],
                "resume_exports": [
                    {
                        "id": row.id,
                        "draft_id": row.draft_id,
                        "version_id": row.version_id,
                        "version": row.version,
                        "page_count": row.page_count,
                        "byte_size": row.byte_size,
                        "pdf_sha256": row.pdf_sha256,
                        "file_name": row.file_name,
                        "created_at": row.created_at,
                    }
                    for row in exports
                ],
                "resume_assets": [
                    {
                        "id": row.id,
                        "draft_id": row.draft_id,
                        "kind": row.kind,
                        "content_type": row.content_type,
                        "byte_size": row.byte_size,
                        "sha256": row.sha256,
                        "created_at": row.created_at,
                    }
                    for row in asset_rows
                ],
            }

            if profile is not None:
                snapshot["career_profile"] = {
                    "id": profile.id,
                    "schema_version": profile.schema_version,
                    "version": profile.version,
                    "headline": profile.headline,
                    "summary": profile.summary,
                    "contacts": _json_value(profile.contacts_json, {}),
                    "goals": _json_value(profile.goals_json, {}),
                    "geography": _json_value(profile.geography_json, {}),
                    "salary": _json_value(profile.salary_json, {}),
                    "skills": _json_value(profile.skills_json, []),
                    "employment": _json_value(profile.employment_json, []),
                    "achievements": _json_value(profile.achievements_json, []),
                    "education": _json_value(profile.education_json, []),
                    "languages": _json_value(profile.languages_json, []),
                    "content_hash": profile.content_hash,
                    "completion_percent": profile.completion_percent,
                    "confirmed_at": profile.confirmed_at,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                }
                snapshot["career_profile_versions"] = [
                    {
                        "id": row.id,
                        "schema_version": row.schema_version,
                        "version": row.version,
                        "snapshot": _json_value(row.snapshot_json, {}),
                        "content_hash": row.content_hash,
                        "changed_sections": _json_value(row.changed_sections_json, []),
                        "source_kind": row.source_kind,
                        "provenance": _json_value(row.provenance_json, {}),
                        "created_at": row.created_at,
                    }
                    for row in profile_versions
                ]

            assets = [
                PrivacyAssetExport(
                    id=row.id,
                    draft_id=row.draft_id,
                    kind=row.kind,
                    content_type=row.content_type,
                    byte_size=row.byte_size,
                    sha256=row.sha256,
                    data=bytes(row.data),
                    created_at=row.created_at,
                )
                for row in asset_rows
            ]
            return snapshot, assets

    def record_export(self, counts: dict[str, int], *, now: int | None = None) -> None:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            session.add(self._audit_row("data_exported", counts, now=timestamp))
            session.commit()

    @staticmethod
    def _delete_legacy_connections(session, oauth_rows: list[OAuthConnection]) -> int:  # noqa: ANN001
        deleted_rows = 0
        for row in oauth_rows:
            result = None
            if row.provider == "superjob":
                try:
                    external_id = int(row.external_user_id)
                except (TypeError, ValueError):
                    continue
                result = session.execute(
                    delete(SuperJobAccount).where(SuperJobAccount.user_id == external_id)
                )
            elif row.provider == "headhunter":
                result = session.execute(
                    delete(HeadHunterAccount).where(
                        HeadHunterAccount.user_id == row.external_user_id
                    )
                )
            if result is not None:
                deleted_rows += max(0, int(result.rowcount or 0))
        return deleted_rows

    def _deletion_counts(self, session, user_id: str) -> dict[str, int]:  # noqa: ANN001
        profile = session.scalar(
            select(CareerProfile).where(CareerProfile.user_id == user_id)
        )
        draft_ids = session.scalars(
            select(ResumeDraft.id).where(ResumeDraft.user_id == user_id)
        ).all()
        counts = {
            "auth_sessions": self._count(session, AuthSession, AuthSession.user_id == user_id),
            "auth_tokens": self._count(session, AuthToken, AuthToken.user_id == user_id),
            "oauth_connections": self._count(
                session, OAuthConnection, OAuthConnection.user_id == user_id
            ),
            "career_profiles": 1 if profile is not None else 0,
            "career_profile_versions": 0,
            "resume_drafts": len(draft_ids),
            "resume_versions": 0,
            "resume_assets": 0,
            "resume_exports": 0,
            "cover_letters": self._count(session, CoverLetter, CoverLetter.user_id == user_id),
            "cover_letter_versions": self._count(session, CoverLetterVersion, CoverLetterVersion.user_id == user_id),
            "cover_letter_proposals": self._count(session, CoverLetterProposal, CoverLetterProposal.user_id == user_id),
            "saved_vacancies": self._count(session, SavedVacancy, SavedVacancy.user_id == user_id),
            "saved_vacancy_sources": self._count(session, SavedVacancySource, SavedVacancySource.user_id == user_id),
            "notification_preferences": self._count(session, NotificationPreference, NotificationPreference.user_id == user_id),
            "saved_vacancy_reminders": self._count(session, SavedVacancyReminder, SavedVacancyReminder.user_id == user_id),
            "saved_vacancy_trackers": self._count(session, SavedVacancyTracker, SavedVacancyTracker.user_id == user_id),
            "saved_vacancy_tracker_events": self._count(
                session, SavedVacancyTrackerEvent, SavedVacancyTrackerEvent.user_id == user_id
            ),
            "vacancy_match_reports": self._count(session, VacancyMatchReport, VacancyMatchReport.user_id == user_id),
            "vacancy_match_series": self._count(session, VacancyMatchSeries, VacancyMatchSeries.user_id == user_id),
            "resume_interview_sessions": self._count(session, ResumeInterviewSession, ResumeInterviewSession.user_id == user_id),
            "resume_analysis_reports": self._count(session, ResumeAnalysisReport, ResumeAnalysisReport.user_id == user_id),
            "ai_consents": self._count(session, AIConsent, AIConsent.user_id == user_id),
        }
        if profile is not None:
            counts["career_profile_versions"] = self._count(
                session,
                CareerProfileVersion,
                CareerProfileVersion.profile_id == profile.id,
            )
        if draft_ids:
            counts["resume_versions"] = self._count(
                session, ResumeVersion, ResumeVersion.draft_id.in_(draft_ids)
            )
            counts["resume_assets"] = self._count(
                session,
                ResumeAsset,
                ResumeAsset.user_id == user_id,
                ResumeAsset.draft_id.in_(draft_ids),
            )
            counts["resume_exports"] = self._count(
                session, ResumeExport, ResumeExport.draft_id.in_(draft_ids)
            )
        return counts

    def delete_account(
        self,
        user_id: str,
        *,
        expected_password_hash: str,
        now: int | None = None,
    ) -> dict[str, int] | None:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            with session.begin():
                statement = select(User).where(User.id == str(user_id))
                if self.engine.dialect.name == "postgresql":
                    statement = statement.with_for_update()
                user = session.scalar(statement)
                if user is None:
                    return None
                if not expected_password_hash or user.password_hash != expected_password_hash:
                    raise PrivacySnapshotConflictError("password_changed")

                # Keep a single lock order for account-destructive operations.
                for model in (AuthSession, AuthToken, OAuthConnection):
                    lock_stmt = select(model.id).where(model.user_id == user.id)
                    if self.engine.dialect.name == "postgresql":
                        lock_stmt = lock_stmt.with_for_update()
                    session.scalars(lock_stmt).all()

                counts = self._deletion_counts(session, user.id)
                counts["ai_usage_events"] = self._count(session, AIUsageEvent, AIUsageEvent.user_id == user.id)
                counts["ai_user_plans"] = self._count(session, AIUserPlan, AIUserPlan.user_id == user.id)
                counts["ai_user_buckets"] = self._count(session, AIBudgetBucket, AIBudgetBucket.user_id == user.id)
                oauth_stmt = select(OAuthConnection).where(OAuthConnection.user_id == user.id)
                if self.engine.dialect.name == "postgresql":
                    oauth_stmt = oauth_stmt.with_for_update()
                oauth_rows = session.scalars(oauth_stmt).all()
                counts["legacy_oauth_mirrors"] = self._delete_legacy_connections(
                    session, list(oauth_rows)
                )
                session.delete(user)
                session.flush()
                session.add(self._audit_row("account_deleted", counts, now=timestamp))
            return counts

    def _asset_is_referenced(self, session, *, asset_id: str, draft_id: str) -> bool:  # noqa: ANN001
        draft_state = session.scalar(
            select(ResumeDraft.state_json).where(ResumeDraft.id == draft_id)
        )
        if _raw_state_references_asset(draft_state, asset_id):
            return True
        version_states = session.scalars(
            select(ResumeVersion.snapshot_json).where(ResumeVersion.draft_id == draft_id)
        ).all()
        return any(_raw_state_references_asset(raw, asset_id) for raw in version_states)

    def _cleanup_orphan_assets(
        self,
        session,  # noqa: ANN001
        *,
        cutoff: int,
        batch_size: int,
    ) -> int:
        candidate_stmt = (
            select(ResumeAsset.id, ResumeAsset.draft_id)
            .where(ResumeAsset.created_at <= int(cutoff))
            .order_by(ResumeAsset.created_at.asc(), ResumeAsset.id.asc())
            .limit(int(batch_size))
        )
        candidates = list(session.execute(candidate_stmt))
        deleted_count = 0
        for asset_id, draft_id in candidates:
            if self._asset_is_referenced(session, asset_id=asset_id, draft_id=draft_id):
                continue
            lock_stmt = select(ResumeAsset.id).where(ResumeAsset.id == asset_id)
            if self.engine.dialect.name == "postgresql":
                lock_stmt = lock_stmt.with_for_update(skip_locked=True)
            locked_id = session.scalar(lock_stmt)
            if locked_id is None:
                continue
            # Recheck after the lock to close the replace/reference race.
            if self._asset_is_referenced(session, asset_id=asset_id, draft_id=draft_id):
                continue
            result = session.execute(delete(ResumeAsset).where(ResumeAsset.id == asset_id))
            deleted_count += max(0, int(result.rowcount or 0))
        return deleted_count

    def cleanup_retention(
        self,
        *,
        pending_account_cutoff: int,
        auth_artifact_cutoff: int,
        audit_cutoff: int,
        orphan_asset_cutoff: int,
        batch_size: int,
        now: int | None = None,
    ) -> dict[str, int]:
        timestamp = int(time.time() if now is None else now)
        limit = max(1, int(batch_size))
        with self.session() as session:
            with session.begin():
                audit_ids = session.scalars(
                    select(PrivacyAuditEvent.id)
                    .where(PrivacyAuditEvent.created_at <= int(audit_cutoff))
                    .order_by(PrivacyAuditEvent.created_at.asc())
                    .limit(limit)
                ).all()
                audit_deleted_count = 0
                if audit_ids:
                    audit_deleted_count = max(0, int(session.execute(
                        delete(PrivacyAuditEvent).where(PrivacyAuditEvent.id.in_(audit_ids))
                    ).rowcount or 0))

                token_ids = session.scalars(
                    select(AuthToken.id)
                    .where(
                        or_(
                            AuthToken.expires_at <= int(auth_artifact_cutoff),
                            AuthToken.consumed_at <= int(auth_artifact_cutoff),
                        )
                    )
                    .order_by(AuthToken.created_at.asc())
                    .limit(limit)
                ).all()
                token_deleted_count = 0
                if token_ids:
                    token_deleted_count = max(0, int(session.execute(
                        delete(AuthToken).where(AuthToken.id.in_(token_ids))
                    ).rowcount or 0))

                session_ids = session.scalars(
                    select(AuthSession.id)
                    .where(
                        or_(
                            AuthSession.expires_at <= int(auth_artifact_cutoff),
                            AuthSession.revoked_at <= int(auth_artifact_cutoff),
                        )
                    )
                    .order_by(AuthSession.created_at.asc())
                    .limit(limit)
                ).all()
                session_deleted_count = 0
                if session_ids:
                    session_deleted_count = max(0, int(session.execute(
                        delete(AuthSession).where(AuthSession.id.in_(session_ids))
                    ).rowcount or 0))

                pending_stmt = (
                    select(User)
                    .where(
                        User.status == "pending",
                        User.created_at <= int(pending_account_cutoff),
                    )
                    .order_by(User.created_at.asc(), User.id.asc())
                    .limit(limit)
                )
                if self.engine.dialect.name == "postgresql":
                    pending_stmt = pending_stmt.with_for_update(skip_locked=True)
                pending_users = session.scalars(pending_stmt).all()
                pending_count = 0
                legacy_mirrors = 0
                for user in pending_users:
                    oauth_rows = session.scalars(
                        select(OAuthConnection).where(OAuthConnection.user_id == user.id)
                    ).all()
                    legacy_mirrors += self._delete_legacy_connections(session, list(oauth_rows))
                    session.delete(user)
                    pending_count += 1

                orphan_assets = self._cleanup_orphan_assets(
                    session,
                    cutoff=int(orphan_asset_cutoff),
                    batch_size=limit,
                )

                counts = {
                    "pending_accounts": pending_count,
                    "auth_sessions": session_deleted_count,
                    "auth_tokens": token_deleted_count,
                    "audit_events": audit_deleted_count,
                    "orphan_resume_assets": orphan_assets,
                    "legacy_oauth_mirrors": legacy_mirrors,
                }
                session.flush()
                session.add(self._audit_row("retention_cleanup", counts, now=timestamp))
            return counts

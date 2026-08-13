"""Repository boundary for PROF-003 server-side resume drafts."""

from __future__ import annotations

import time
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from domain import (
    ResumeAssetRecord,
    ResumeDraftRecord,
    ResumeExportRecord,
    ResumeVersionRecord,
)
from models import ResumeAsset, ResumeDraft, ResumeExport, ResumeVersion

from .base import RepositoryBase


class ResumeDraftConflictError(RuntimeError):
    """Raised when a stale editor attempts to overwrite a newer draft."""


class ResumeDraftNotFoundError(LookupError):
    """Raised when an owner-scoped draft does not exist."""


class ResumeDraftRepository(RepositoryBase):
    """Owner-scoped draft persistence, immutable versions, and assets."""

    @staticmethod
    def _draft_record(row: ResumeDraft) -> ResumeDraftRecord:
        return ResumeDraftRecord(
            id=row.id,
            user_id=row.user_id,
            schema_version=row.schema_version,
            revision=row.revision,
            title=row.title,
            state_json=row.state_json,
            content_hash=row.content_hash,
            completion_percent=row.completion_percent,
            profile_version=row.profile_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _version_record(row: ResumeVersion) -> ResumeVersionRecord:
        return ResumeVersionRecord(
            id=row.id,
            draft_id=row.draft_id,
            schema_version=row.schema_version,
            version=row.version,
            draft_revision=row.draft_revision,
            snapshot_json=row.snapshot_json,
            content_hash=row.content_hash,
            reason=row.reason,
            restored_from_version=row.restored_from_version,
            created_at=row.created_at,
        )

    @staticmethod
    def _asset_record(row: ResumeAsset) -> ResumeAssetRecord:
        return ResumeAssetRecord(
            id=row.id,
            draft_id=row.draft_id,
            user_id=row.user_id,
            kind=row.kind,
            content_type=row.content_type,
            byte_size=row.byte_size,
            sha256=row.sha256,
            data=bytes(row.data),
            created_at=row.created_at,
        )

    @staticmethod
    def _export_record(row: ResumeExport) -> ResumeExportRecord:
        return ResumeExportRecord(
            id=row.id,
            draft_id=row.draft_id,
            version_id=row.version_id,
            version=row.version,
            page_count=row.page_count,
            byte_size=row.byte_size,
            pdf_sha256=row.pdf_sha256,
            file_name=row.file_name,
            created_at=row.created_at,
        )

    @staticmethod
    def _lock_owned_draft(session, *, user_id: str, draft_id: str) -> ResumeDraft | None:  # noqa: ANN001
        statement = select(ResumeDraft).where(
            ResumeDraft.id == str(draft_id),
            ResumeDraft.user_id == str(user_id),
        )
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            statement = statement.with_for_update()
        return session.scalar(statement)

    def list_by_user(self, *, user_id: str, limit: int = 50) -> list[ResumeDraftRecord]:
        bounded = min(max(int(limit), 1), 100)
        with self.session() as session:
            rows = session.scalars(
                select(ResumeDraft)
                .where(ResumeDraft.user_id == str(user_id))
                .order_by(ResumeDraft.updated_at.desc(), ResumeDraft.created_at.desc())
                .limit(bounded)
            ).all()
            return [self._draft_record(row) for row in rows]

    def latest_by_user(self, *, user_id: str) -> ResumeDraftRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(ResumeDraft)
                .where(ResumeDraft.user_id == str(user_id))
                .order_by(ResumeDraft.updated_at.desc(), ResumeDraft.created_at.desc())
                .limit(1)
            )
            return self._draft_record(row) if row else None

    def get_by_owner(self, *, user_id: str, draft_id: str) -> ResumeDraftRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(ResumeDraft).where(
                    ResumeDraft.id == str(draft_id),
                    ResumeDraft.user_id == str(user_id),
                )
            )
            return self._draft_record(row) if row else None

    def create(
        self,
        *,
        user_id: str,
        title: str,
        schema_version: int,
        state_json: str,
        content_hash: str,
        completion_percent: int,
        profile_version: int | None,
        now: int | None = None,
    ) -> ResumeDraftRecord:
        timestamp = int(time.time() if now is None else now)
        row = ResumeDraft(
            id=str(uuid.uuid4()),
            user_id=str(user_id),
            schema_version=int(schema_version),
            revision=1,
            title=str(title),
            state_json=str(state_json),
            content_hash=str(content_hash),
            completion_percent=int(completion_percent),
            profile_version=(None if profile_version is None else int(profile_version)),
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self.session() as session:
            session.add(row)
            session.commit()
            return self._draft_record(row)

    def save_state(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
        schema_version: int,
        state_json: str,
        content_hash: str,
        completion_percent: int,
        now: int | None = None,
    ) -> tuple[ResumeDraftRecord, bool]:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            row = self._lock_owned_draft(
                session,
                user_id=str(user_id),
                draft_id=str(draft_id),
            )
            if row is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            if row.revision != int(expected_revision):
                raise ResumeDraftConflictError(
                    "Черновик изменён в другой вкладке или на другом устройстве. Обновите страницу."
                )
            if row.content_hash == str(content_hash):
                return self._draft_record(row), False
            row.schema_version = int(schema_version)
            row.revision += 1
            row.state_json = str(state_json)
            row.content_hash = str(content_hash)
            row.completion_percent = int(completion_percent)
            row.updated_at = timestamp
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ResumeDraftConflictError(
                    "Черновик изменён в другой вкладке или на другом устройстве. Обновите страницу."
                ) from exc
            return self._draft_record(row), True

    def rename(
        self,
        *,
        user_id: str,
        draft_id: str,
        title: str,
        now: int | None = None,
    ) -> ResumeDraftRecord:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            row = self._lock_owned_draft(session, user_id=user_id, draft_id=draft_id)
            if row is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            row.title = str(title)
            row.updated_at = timestamp
            session.commit()
            return self._draft_record(row)

    def delete(self, *, user_id: str, draft_id: str) -> bool:
        with self.session() as session:
            row = self._lock_owned_draft(session, user_id=user_id, draft_id=draft_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def counts(self, *, user_id: str, draft_id: str) -> tuple[int, int]:
        with self.session() as session:
            owned = session.scalar(
                select(ResumeDraft.id).where(
                    ResumeDraft.id == str(draft_id),
                    ResumeDraft.user_id == str(user_id),
                )
            )
            if owned is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            version_count = int(
                session.scalar(
                    select(func.count(ResumeVersion.id)).where(
                        ResumeVersion.draft_id == str(draft_id)
                    )
                )
                or 0
            )
            export_count = int(
                session.scalar(
                    select(func.count(ResumeExport.id)).where(
                        ResumeExport.draft_id == str(draft_id)
                    )
                )
                or 0
            )
            return version_count, export_count

    def list_versions(
        self,
        *,
        user_id: str,
        draft_id: str,
        limit: int = 100,
    ) -> list[ResumeVersionRecord]:
        bounded = min(max(int(limit), 1), 200)
        with self.session() as session:
            rows = session.scalars(
                select(ResumeVersion)
                .join(ResumeDraft, ResumeDraft.id == ResumeVersion.draft_id)
                .where(
                    ResumeDraft.user_id == str(user_id),
                    ResumeVersion.draft_id == str(draft_id),
                )
                .order_by(ResumeVersion.version.desc())
                .limit(bounded)
            ).all()
            return [self._version_record(row) for row in rows]

    def get_version(
        self,
        *,
        user_id: str,
        draft_id: str,
        version: int,
    ) -> ResumeVersionRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(ResumeVersion)
                .join(ResumeDraft, ResumeDraft.id == ResumeVersion.draft_id)
                .where(
                    ResumeDraft.user_id == str(user_id),
                    ResumeVersion.draft_id == str(draft_id),
                    ResumeVersion.version == int(version),
                )
            )
            return self._version_record(row) if row else None

    @staticmethod
    def _ensure_version(
        session,
        *,
        draft: ResumeDraft,
        reason: str,
        restored_from_version: int | None,
        timestamp: int,
    ) -> tuple[ResumeVersion, bool]:  # noqa: ANN001
        latest = session.scalar(
            select(ResumeVersion)
            .where(ResumeVersion.draft_id == draft.id)
            .order_by(ResumeVersion.version.desc())
            .limit(1)
        )
        if latest is not None and latest.content_hash == draft.content_hash:
            return latest, False
        version_number = 1 if latest is None else latest.version + 1
        row = ResumeVersion(
            id=str(uuid.uuid4()),
            draft_id=draft.id,
            schema_version=draft.schema_version,
            version=version_number,
            draft_revision=draft.revision,
            snapshot_json=draft.state_json,
            content_hash=draft.content_hash,
            reason=str(reason),
            restored_from_version=(
                None if restored_from_version is None else int(restored_from_version)
            ),
            created_at=timestamp,
        )
        session.add(row)
        session.flush()
        return row, True

    def create_checkpoint(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
        reason: str = "checkpoint",
        now: int | None = None,
    ) -> tuple[ResumeVersionRecord, bool]:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            draft = self._lock_owned_draft(
                session,
                user_id=user_id,
                draft_id=draft_id,
            )
            if draft is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            if draft.revision != int(expected_revision):
                raise ResumeDraftConflictError(
                    "Черновик изменён в другой вкладке или на другом устройстве. Обновите страницу."
                )
            version_row, created = self._ensure_version(
                session,
                draft=draft,
                reason=str(reason),
                restored_from_version=None,
                timestamp=timestamp,
            )
            session.commit()
            return self._version_record(version_row), created

    def restore_version(
        self,
        *,
        user_id: str,
        draft_id: str,
        version: int,
        expected_revision: int,
        completion_percent: int,
        now: int | None = None,
    ) -> tuple[ResumeDraftRecord, ResumeVersionRecord]:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            draft = self._lock_owned_draft(
                session,
                user_id=user_id,
                draft_id=draft_id,
            )
            if draft is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            if draft.revision != int(expected_revision):
                raise ResumeDraftConflictError(
                    "Черновик изменён в другой вкладке или на другом устройстве. Обновите страницу."
                )
            source = session.scalar(
                select(ResumeVersion).where(
                    ResumeVersion.draft_id == draft.id,
                    ResumeVersion.version == int(version),
                )
            )
            if source is None:
                raise ResumeDraftNotFoundError("Версия резюме не найдена.")
            draft.schema_version = source.schema_version
            draft.revision += 1
            draft.state_json = source.snapshot_json
            draft.content_hash = source.content_hash
            draft.completion_percent = int(completion_percent)
            draft.updated_at = timestamp
            latest = session.scalar(
                select(ResumeVersion)
                .where(ResumeVersion.draft_id == draft.id)
                .order_by(ResumeVersion.version.desc())
                .limit(1)
            )
            version_number = 1 if latest is None else latest.version + 1
            restored = ResumeVersion(
                id=str(uuid.uuid4()),
                draft_id=draft.id,
                schema_version=source.schema_version,
                version=version_number,
                draft_revision=draft.revision,
                snapshot_json=source.snapshot_json,
                content_hash=source.content_hash,
                reason="restore",
                restored_from_version=source.version,
                created_at=timestamp,
            )
            session.add(restored)
            session.commit()
            return self._draft_record(draft), self._version_record(restored)

    def store_asset(
        self,
        *,
        user_id: str,
        draft_id: str,
        kind: str,
        content_type: str,
        data: bytes,
        sha256: str,
        now: int | None = None,
    ) -> ResumeAssetRecord:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            owned = session.scalar(
                select(ResumeDraft.id).where(
                    ResumeDraft.id == str(draft_id),
                    ResumeDraft.user_id == str(user_id),
                )
            )
            if owned is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            existing = session.scalar(
                select(ResumeAsset).where(
                    ResumeAsset.draft_id == str(draft_id),
                    ResumeAsset.kind == str(kind),
                    ResumeAsset.sha256 == str(sha256),
                )
            )
            if existing is not None:
                return self._asset_record(existing)
            row = ResumeAsset(
                id=str(uuid.uuid4()),
                draft_id=str(draft_id),
                user_id=str(user_id),
                kind=str(kind),
                content_type=str(content_type),
                byte_size=len(data),
                sha256=str(sha256),
                data=bytes(data),
                created_at=timestamp,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                duplicate = session.scalar(
                    select(ResumeAsset).where(
                        ResumeAsset.draft_id == str(draft_id),
                        ResumeAsset.kind == str(kind),
                        ResumeAsset.sha256 == str(sha256),
                    )
                )
                if duplicate is None:
                    raise
                return self._asset_record(duplicate)
            return self._asset_record(row)

    def get_asset(self, *, user_id: str, asset_id: str) -> ResumeAssetRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(ResumeAsset).where(
                    ResumeAsset.id == str(asset_id),
                    ResumeAsset.user_id == str(user_id),
                )
            )
            return self._asset_record(row) if row else None

    def asset_belongs_to_draft(
        self,
        *,
        user_id: str,
        draft_id: str,
        asset_id: str,
        kind: str,
    ) -> bool:
        with self.session() as session:
            found = session.scalar(
                select(ResumeAsset.id).where(
                    ResumeAsset.id == str(asset_id),
                    ResumeAsset.user_id == str(user_id),
                    ResumeAsset.draft_id == str(draft_id),
                    ResumeAsset.kind == str(kind),
                )
            )
            return found is not None

    def record_export(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
        page_count: int,
        byte_size: int,
        pdf_sha256: str,
        file_name: str,
        now: int | None = None,
    ) -> tuple[ResumeExportRecord, ResumeVersionRecord, bool]:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            draft = self._lock_owned_draft(
                session,
                user_id=user_id,
                draft_id=draft_id,
            )
            if draft is None:
                raise ResumeDraftNotFoundError("Черновик не найден.")
            if draft.revision != int(expected_revision):
                raise ResumeDraftConflictError(
                    "Черновик изменён до экспорта. Обновите страницу и повторите скачивание."
                )
            version_row, created = self._ensure_version(
                session,
                draft=draft,
                reason="export",
                restored_from_version=None,
                timestamp=timestamp,
            )
            export_row = ResumeExport(
                id=str(uuid.uuid4()),
                draft_id=draft.id,
                version_id=version_row.id,
                version=version_row.version,
                page_count=int(page_count),
                byte_size=int(byte_size),
                pdf_sha256=str(pdf_sha256),
                file_name=str(file_name),
                created_at=timestamp,
            )
            session.add(export_row)
            session.commit()
            return (
                self._export_record(export_row),
                self._version_record(version_row),
                created,
            )

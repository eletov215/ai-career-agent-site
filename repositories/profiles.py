"""Repository boundary for PROF-001 structured career profiles."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from domain import CareerProfileRecord, CareerProfileVersionRecord
from models import CareerProfile, CareerProfileVersion

from .base import RepositoryBase


class CareerProfileVersionConflictError(RuntimeError):
    """Raised when an editor attempts to overwrite a newer profile version."""


class CareerProfileRepository(RepositoryBase):
    """Owner-scoped profile persistence with immutable snapshots."""

    _SECTION_COLUMNS = {
        "contacts": "contacts_json",
        "goals": "goals_json",
        "geography": "geography_json",
        "salary": "salary_json",
        "skills": "skills_json",
        "employment": "employment_json",
        "achievements": "achievements_json",
        "education": "education_json",
        "languages": "languages_json",
    }

    @staticmethod
    def _record(row: CareerProfile) -> CareerProfileRecord:
        return CareerProfileRecord(
            id=row.id,
            user_id=row.user_id,
            schema_version=row.schema_version,
            version=row.version,
            headline=row.headline,
            summary=row.summary,
            contacts_json=row.contacts_json,
            goals_json=row.goals_json,
            geography_json=row.geography_json,
            salary_json=row.salary_json,
            skills_json=row.skills_json,
            employment_json=row.employment_json,
            achievements_json=row.achievements_json,
            education_json=row.education_json,
            languages_json=row.languages_json,
            content_hash=row.content_hash,
            completion_percent=row.completion_percent,
            confirmed_at=row.confirmed_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _version_record(row: CareerProfileVersion) -> CareerProfileVersionRecord:
        return CareerProfileVersionRecord(
            id=row.id,
            profile_id=row.profile_id,
            schema_version=row.schema_version,
            version=row.version,
            snapshot_json=row.snapshot_json,
            content_hash=row.content_hash,
            changed_sections_json=row.changed_sections_json,
            source_kind=row.source_kind,
            provenance_json=row.provenance_json,
            created_at=row.created_at,
        )

    def get_by_user(self, user_id: str) -> CareerProfileRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(CareerProfile).where(CareerProfile.user_id == str(user_id))
            )
            return self._record(row) if row else None

    def list_versions(
        self,
        *,
        user_id: str,
        limit: int = 20,
    ) -> list[CareerProfileVersionRecord]:
        bounded_limit = min(max(int(limit), 1), 100)
        with self.session() as session:
            rows = session.scalars(
                select(CareerProfileVersion)
                .join(
                    CareerProfile,
                    CareerProfile.id == CareerProfileVersion.profile_id,
                )
                .where(CareerProfile.user_id == str(user_id))
                .order_by(CareerProfileVersion.version.desc())
                .limit(bounded_limit)
            ).all()
            return [self._version_record(row) for row in rows]

    def get_version(
        self,
        *,
        user_id: str,
        version: int,
    ) -> CareerProfileVersionRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(CareerProfileVersion)
                .join(
                    CareerProfile,
                    CareerProfile.id == CareerProfileVersion.profile_id,
                )
                .where(
                    CareerProfile.user_id == str(user_id),
                    CareerProfileVersion.version == int(version),
                )
            )
            return self._version_record(row) if row else None

    def save_snapshot(
        self,
        *,
        user_id: str,
        expected_version: int,
        schema_version: int,
        headline: str | None,
        summary: str | None,
        section_json: Mapping[str, str],
        snapshot_json: str,
        content_hash: str,
        completion_percent: int,
        changed_sections: Sequence[str],
        source_kind: str,
        provenance_json: str,
        now: int | None = None,
    ) -> tuple[CareerProfileRecord, bool]:
        timestamp = int(time.time() if now is None else now)
        with self.session() as session:
            statement = select(CareerProfile).where(
                CareerProfile.user_id == str(user_id)
            )
            if self.engine.dialect.name == "postgresql":
                statement = statement.with_for_update()
            row = session.scalar(statement)

            if row is None:
                if int(expected_version) != 0:
                    raise CareerProfileVersionConflictError(
                        "Профиль был изменён в другой сессии. Обновите страницу."
                    )
                row = CareerProfile(
                    id=str(uuid.uuid4()),
                    user_id=str(user_id),
                    schema_version=int(schema_version),
                    version=1,
                    headline=headline,
                    summary=summary,
                    contacts_json=section_json["contacts"],
                    goals_json=section_json["goals"],
                    geography_json=section_json["geography"],
                    salary_json=section_json["salary"],
                    skills_json=section_json["skills"],
                    employment_json=section_json["employment"],
                    achievements_json=section_json["achievements"],
                    education_json=section_json["education"],
                    languages_json=section_json["languages"],
                    content_hash=content_hash,
                    completion_percent=int(completion_percent),
                    confirmed_at=timestamp,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                session.add(row)
                version_number = 1
            else:
                if row.version != int(expected_version):
                    raise CareerProfileVersionConflictError(
                        "Профиль был изменён в другой сессии. Обновите страницу."
                    )
                if row.content_hash == content_hash:
                    return self._record(row), False
                version_number = row.version + 1
                row.schema_version = int(schema_version)
                row.version = version_number
                row.headline = headline
                row.summary = summary
                for section, column in self._SECTION_COLUMNS.items():
                    setattr(row, column, section_json[section])
                row.content_hash = content_hash
                row.completion_percent = int(completion_percent)
                row.confirmed_at = timestamp
                row.updated_at = timestamp

            session.add(
                CareerProfileVersion(
                    id=str(uuid.uuid4()),
                    profile_id=row.id,
                    schema_version=int(schema_version),
                    version=version_number,
                    snapshot_json=snapshot_json,
                    content_hash=content_hash,
                    changed_sections_json=json.dumps(
                        list(changed_sections),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    source_kind=str(source_kind),
                    provenance_json=str(provenance_json),
                    created_at=timestamp,
                )
            )
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise CareerProfileVersionConflictError(
                    "Профиль был изменён в другой сессии. Обновите страницу."
                ) from exc
            return self._record(row), True

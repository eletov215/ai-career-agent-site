"""Bounded, owner-scoped read model for JOB-004 analytics."""
from __future__ import annotations

from sqlalchemy import case, distinct, exists, func, select

from models.application_tracker import SavedVacancyTracker, SavedVacancyTrackerEvent
from models.saved_vacancy import SavedVacancy, SavedVacancySource
from .base import RepositoryBase


STATES = (
    "saved", "preparing", "submitted_user_reported",
    "in_process_user_reported", "closed",
)
MILESTONES = (
    "preparing", "submitted_user_reported", "in_process_user_reported",
)


class JobAnalyticsRepository(RepositoryBase):
    """Compute one owner's view in two queries, independent of cohort size."""

    def source_choices(self, user_id: str) -> tuple[str, ...]:
        with self.session() as session:
            rows = session.scalars(
                select(distinct(SavedVacancySource.source))
                .where(SavedVacancySource.user_id == user_id)
                .order_by(SavedVacancySource.source)
            ).all()
            return tuple(rows)

    def metrics(self, user_id: str, *, saved_since: int | None, source: str | None) -> dict:
        current_state = func.coalesce(SavedVacancyTracker.state, "saved")
        columns = [func.count(distinct(SavedVacancy.id)).label("saved_count")]
        for milestone in MILESTONES:
            reached = exists().where(
                SavedVacancyTrackerEvent.user_id == user_id,
                SavedVacancyTrackerEvent.saved_vacancy_id == SavedVacancy.id,
                SavedVacancyTrackerEvent.to_state == milestone,
            )
            label = {
                "preparing": "preparing_ever_count",
                "submitted_user_reported": "submitted_ever_count",
                "in_process_user_reported": "in_process_ever_count",
            }[milestone]
            columns.append(func.sum(case((reached, 1), else_=0)).label(label))
        columns.extend([
            func.sum(case((current_state != "closed", 1), else_=0)).label("active_pipeline_count"),
            func.sum(case((current_state == "closed", 1), else_=0)).label("closed_current_count"),
        ])
        columns.extend(
            func.sum(case((current_state == state, 1), else_=0)).label(f"state_{state}")
            for state in STATES
        )
        query = select(*columns).select_from(SavedVacancy).outerjoin(
            SavedVacancyTracker,
            (SavedVacancyTracker.saved_vacancy_id == SavedVacancy.id)
            & (SavedVacancyTracker.user_id == user_id),
        ).where(SavedVacancy.user_id == user_id)
        if saved_since is not None:
            query = query.where(SavedVacancy.created_at >= saved_since)
        if source is not None:
            query = query.where(exists().where(
                SavedVacancySource.user_id == user_id,
                SavedVacancySource.saved_vacancy_id == SavedVacancy.id,
                SavedVacancySource.source == source,
            ))
        with self.session() as session:
            row = session.execute(query).one()._mapping
        return {key: int(row[key] or 0) for key in row}

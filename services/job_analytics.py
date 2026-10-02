"""Truthful presentation rules for personal job-search analytics."""
from __future__ import annotations

from dataclasses import dataclass
import time


PERIOD_DAYS = {"7": 7, "30": 30, "90": 90, "all": None}


@dataclass(frozen=True, slots=True)
class Conversion:
    numerator: int
    denominator: int
    percentage: float | None
    caveat: str | None


def conversion(numerator: int, denominator: int) -> Conversion:
    if denominator == 0:
        return Conversion(numerator, denominator, None, "Нет данных для расчёта.")
    if denominator < 5:
        return Conversion(numerator, denominator, None, "Слишком мало данных для содержательного процента.")
    percentage = round(numerator * 100 / denominator, 1)
    caveat = "Малая выборка: результат может заметно меняться." if denominator < 20 else None
    return Conversion(numerator, denominator, percentage, caveat)


class JobAnalyticsService:
    def __init__(self, repository, *, clock=time.time):
        self.repository = repository
        self.clock = clock

    def report(self, user_id: str, *, period: str = "30", source: str | None = None) -> dict:
        if period not in PERIOD_DAYS:
            period = "30"
        choices = self.repository.source_choices(user_id)
        # An unknown value is indistinguishable from an unowned one and yields no cohort.
        invalid_source = source is not None and source not in choices
        days = PERIOD_DAYS[period]
        since = None if days is None else int(self.clock()) - days * 86_400
        metrics = self.repository.metrics(
            user_id, saved_since=since, source=source if not invalid_source else "__invalid_source__"
        )
        metrics["current_state_distribution"] = {
            state: metrics.pop(f"state_{state}")
            for state in ("saved", "preparing", "submitted_user_reported", "in_process_user_reported", "closed")
        }
        metrics["saved_to_submitted"] = conversion(
            metrics["submitted_ever_count"], metrics["saved_count"]
        )
        metrics["submitted_to_in_process"] = conversion(
            metrics["in_process_ever_count"], metrics["submitted_ever_count"]
        )
        return {"period": period, "source": source, "sources": choices, "invalid_source": invalid_source, **metrics}

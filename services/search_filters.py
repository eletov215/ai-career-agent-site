from __future__ import annotations

from dataclasses import dataclass


ALLOWED_PERIOD_DAYS = {1, 3, 7, 14, 30}
ALLOWED_SORTS = {"date", "salary_desc", "salary_asc", "relevance"}


@dataclass(frozen=True)
class VacancySearchFilters:
    keyword: str = ""
    remote_only: bool = False
    salary_from: int | None = None
    salary_only: bool = False
    period_days: int = 7
    sort: str = "date"

    @classmethod
    def from_query(cls, args) -> "VacancySearchFilters":
        keyword = str(args.get("keyword", "") or "").strip()
        remote_only = args.get("remote") == "1"
        salary_only = args.get("salary_only") == "1"

        try:
            salary_value = int(str(args.get("salary_from", "") or "").strip())
            salary_from = max(salary_value, 0) or None
        except ValueError:
            salary_from = None

        try:
            period_days = int(args.get("period", "7") or 7)
        except ValueError:
            period_days = 7
        if period_days not in ALLOWED_PERIOD_DAYS:
            period_days = 7

        sort = str(args.get("sort", "date") or "date").strip()
        if sort not in ALLOWED_SORTS:
            sort = "date"

        return cls(
            keyword=keyword,
            remote_only=remote_only,
            salary_from=salary_from,
            salary_only=salary_only,
            period_days=period_days,
            sort=sort,
        )

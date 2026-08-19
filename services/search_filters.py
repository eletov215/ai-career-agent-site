from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from .vacancy_normalizer import canonical_currency, normalize_datetime


ALLOWED_PERIOD_DAYS = {1, 3, 7, 14, 30}
ALLOWED_SORTS = {"date", "salary_desc", "salary_asc", "relevance"}
ALLOWED_EXPERIENCE = {"", "no_experience", "between_1_and_3", "between_3_and_6", "more_than_6"}
ALLOWED_EMPLOYMENT = {"", "full", "part", "project", "probation", "volunteer"}
ALLOWED_WORK_FORMATS = {"", "onsite", "remote", "hybrid"}
ALLOWED_CURRENCIES = {"", "RUB", "USD", "EUR", "GBP", "KZT", "BYN"}


@dataclass(frozen=True)
class VacancySearchFilters:
    keyword: str = ""
    region: str = ""
    experience: str = ""
    employment: str = ""
    work_format: str = ""
    currency: str = ""
    remote_only: bool = False
    salary_from: int | None = None
    salary_only: bool = False
    period_days: int = 7
    sort: str = "date"

    @classmethod
    def from_query(cls, args) -> "VacancySearchFilters":  # noqa: ANN001
        keyword = str(args.get("keyword", "") or "").strip()
        region = str(args.get("region", "") or "").strip()
        remote_only = args.get("remote") == "1"
        salary_only = args.get("salary_only") == "1"

        experience = str(args.get("experience", "") or "").strip()
        if experience not in ALLOWED_EXPERIENCE:
            experience = ""

        employment = str(args.get("employment", "") or "").strip()
        if employment not in ALLOWED_EMPLOYMENT:
            employment = ""

        work_format = str(args.get("work_format", "") or "").strip()
        if work_format not in ALLOWED_WORK_FORMATS:
            work_format = ""
        if remote_only and not work_format:
            work_format = "remote"

        currency = canonical_currency(args.get("currency", ""))
        if currency not in ALLOWED_CURRENCIES:
            currency = ""

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
            region=region,
            experience=experience,
            employment=employment,
            work_format=work_format,
            currency=currency,
            remote_only=(work_format == "remote"),
            salary_from=salary_from,
            salary_only=salary_only,
            period_days=period_days,
            sort=sort,
        )

    def query_pairs(self) -> list[tuple[str, str]]:
        pairs = [
            ("search", "1"),
            ("keyword", self.keyword),
            ("period", str(self.period_days)),
            ("sort", self.sort),
        ]
        for name, value in (
            ("region", self.region),
            ("experience", self.experience),
            ("employment", self.employment),
            ("work_format", self.work_format),
            ("currency", self.currency),
        ):
            if value:
                pairs.append((name, value))
        if self.salary_from is not None:
            pairs.append(("salary_from", str(self.salary_from)))
        if self.salary_only:
            pairs.append(("salary_only", "1"))
        return pairs


def _salary_value(item: Mapping[str, Any]) -> float:
    for name in ("salary_to", "salary_from"):
        value = item.get(name)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def vacancy_matches_filters(
    item: Mapping[str, Any],
    filters: VacancySearchFilters,
    *,
    now: datetime | None = None,
) -> bool:
    """Apply one canonical filter policy to cached and direct providers."""

    text = " ".join(
        str(item.get(field) or "")
        for field in ("title", "company", "location", "description", "requirements")
    ).casefold()
    if filters.keyword:
        if not all(term.casefold() in text for term in filters.keyword.split() if term.strip()):
            return False
    if (
        filters.region
        and not filters.region.isdigit()
        and filters.region.casefold() not in str(item.get("location") or "").casefold()
    ):
        return False

    work_format = str(item.get("work_format") or "unknown").casefold()
    if filters.work_format and work_format != filters.work_format:
        return False
    if filters.remote_only and work_format != "remote":
        return False

    employment_code = str(item.get("employment_code") or "unknown").casefold()
    if filters.employment and employment_code != filters.employment:
        return False

    experience_code = str(item.get("experience_code") or "unknown").casefold()
    if filters.experience and experience_code != filters.experience:
        return False

    if filters.currency and canonical_currency(item.get("currency")) != filters.currency:
        return False
    has_salary = item.get("salary_from") is not None or item.get("salary_to") is not None
    if filters.salary_only and not has_salary:
        return False
    if filters.salary_from is not None and _salary_value(item) < filters.salary_from:
        return False

    if filters.period_days > 0:
        published = normalize_datetime(item.get("published_at"))
        if published:
            try:
                parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
            if parsed is not None:
                reference = now or datetime.now(timezone.utc)
                if reference.tzinfo is None:
                    reference = reference.replace(tzinfo=timezone.utc)
                if parsed < reference.astimezone(timezone.utc) - timedelta(days=filters.period_days):
                    return False
    return str(item.get("source_status") or "active").casefold() == "active"


def filter_vacancies(
    items: Iterable[dict[str, Any]],
    filters: VacancySearchFilters,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    return [item for item in items if vacancy_matches_filters(item, filters, now=now)]

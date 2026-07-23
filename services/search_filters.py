from __future__ import annotations

from dataclasses import dataclass


ALLOWED_PERIOD_DAYS = {1, 3, 7, 14, 30}
ALLOWED_SORTS = {"date", "salary_desc", "salary_asc", "relevance"}
ALLOWED_EXPERIENCE = {"", "no_experience", "between_1_and_3", "between_3_and_6", "more_than_6"}
ALLOWED_EMPLOYMENT = {"", "full", "part", "project", "probation", "volunteer"}
ALLOWED_WORK_FORMATS = {"", "onsite", "remote", "hybrid"}
ALLOWED_CURRENCIES = {"", "RUB", "USD", "EUR", "GBP", "KZT", "BYN"}


def canonical_currency(value: str | None) -> str:
    currency = str(value or "").strip().upper()
    aliases = {
        "RUR": "RUB",
        "BYR": "BYN",
    }
    return aliases.get(currency, currency)


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
    def from_query(cls, args) -> "VacancySearchFilters":
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
        pairs = [("search", "1"), ("keyword", self.keyword), ("period", str(self.period_days)), ("sort", self.sort)]
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

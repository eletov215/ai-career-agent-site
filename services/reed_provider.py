from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters, canonical_currency


class ReedProvider(VacancyProvider):
    key = "reed"
    title = "Reed.co.uk"

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://www.reed.co.uk/api/1.0/search",
        per_page: int = 60,
        timeout: int = 10,
    ):
        self.api_key = api_key.strip()
        self.api_url = api_url
        self.per_page = max(1, min(per_page, 100))
        self.timeout = timeout

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        description = raw.get("jobDescription") or raw.get("description") or ""
        location = raw.get("locationName") or raw.get("location") or ""
        title = raw.get("jobTitle") or raw.get("title") or "Без названия"
        combined_text = f"{title} {description} {location}".casefold()
        remote = any(term in combined_text for term in ("remote", "home based", "work from home"))

        return {
            "external_id": str(raw.get("jobId") or raw.get("id") or ""),
            "source": "reed",
            "source_title": "Reed.co.uk",
            "title": title,
            "company": raw.get("employerName") or "Компания не указана",
            "salary_from": raw.get("minimumSalary"),
            "salary_to": raw.get("maximumSalary"),
            "currency": canonical_currency(raw.get("currency") or "GBP"),
            "location": location,
            "remote": remote,
            "schedule": raw.get("jobType") or "",
            "employment": raw.get("contractType") or raw.get("jobType") or "",
            "experience": "",
            "description": description,
            "requirements": "",
            "published_at": raw.get("date") or raw.get("datePosted") or "",
            "url": raw.get("jobUrl") or raw.get("externalUrl") or "",
        }

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def search(self, *, filters: VacancySearchFilters, page: int = 0) -> SearchResult:
        params: dict[str, Any] = {
            "resultsToTake": self.per_page,
            "resultsToSkip": page * self.per_page,
        }
        if filters.keyword:
            params["keywords"] = filters.keyword
        if filters.region:
            params["locationName"] = filters.region
        if filters.salary_from is not None:
            params["minimumSalary"] = filters.salary_from
        if filters.employment == "full":
            params["fullTime"] = "true"
        elif filters.employment == "part":
            params["partTime"] = "true"
        elif filters.employment == "project":
            params["contract"] = "true"

        try:
            response = requests.get(
                self.api_url,
                params=params,
                auth=(self.api_key, ""),
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            raw_items = payload.get("results", []) if isinstance(payload, dict) else []
            items = [self._normalize(item) for item in raw_items if isinstance(item, dict)]

            cutoff = datetime.now(timezone.utc) - timedelta(days=filters.period_days)
            dated_items = []
            for item in items:
                published = self._parse_date(item.get("published_at"))
                if published is None or published >= cutoff:
                    dated_items.append(item)
            items = dated_items

            if filters.work_format == "remote":
                items = [item for item in items if item.get("remote")]
            elif filters.work_format == "onsite":
                items = [item for item in items if not item.get("remote")]
            elif filters.work_format == "hybrid":
                items = [
                    item for item in items
                    if "hybrid" in f"{item.get('title', '')} {item.get('description', '')}".casefold()
                ]
            if filters.salary_only:
                items = [item for item in items if item.get("salary_from") is not None or item.get("salary_to") is not None]
            if filters.currency:
                items = [item for item in items if canonical_currency(item.get("currency")) == filters.currency]

            total = int(payload.get("totalResults", 0) or 0) if isinstance(payload, dict) else 0
            return SearchResult(
                items=items,
                total=total,
                page=page,
                pages=(total + self.per_page - 1) // self.per_page if total else 0,
                has_next=(page + 1) * self.per_page < total,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "HTTP"
            return SearchResult(page=page, error=f"Reed.co.uk: ошибка API {status}")
        except (requests.RequestException, ValueError) as exc:
            return SearchResult(page=page, error=f"Reed.co.uk: {exc}")

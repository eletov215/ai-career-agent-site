from __future__ import annotations

import logging
from typing import Any

import requests

from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters, filter_vacancies
from .vacancy_normalizer import normalize_reed_vacancy

logger = logging.getLogger(__name__)


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
        return normalize_reed_vacancy(raw).as_mapping()

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

            items = filter_vacancies(items, filters)

            total = int(payload.get("totalResults", 0) or 0) if isinstance(payload, dict) else 0
            return SearchResult(
                items=items,
                total=total,
                page=page,
                pages=(total + self.per_page - 1) // self.per_page if total else 0,
                has_next=(page + 1) * self.per_page < total,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            logger.exception("Reed vacancy search failed status=%s", status)
            message = "Reed.co.uk временно не смог выполнить поиск."
            if status in {401, 403, 429}:
                message += f" Доступ источника отклонён (HTTP {status})."
            return SearchResult(page=page, error=message)
        except requests.RequestException:
            logger.exception("Reed vacancy search failed")
            return SearchResult(
                page=page,
                error="Reed.co.uk временно не смог выполнить поиск.",
            )
        except (ValueError, TypeError, KeyError):
            logger.exception("Reed returned invalid vacancy payload")
            return SearchResult(
                page=page,
                error="Reed.co.uk вернул некорректный ответ.",
            )

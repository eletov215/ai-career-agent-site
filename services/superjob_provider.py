from __future__ import annotations

import logging
from typing import Callable, Optional

import requests

from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters, filter_vacancies
from .vacancy_normalizer import normalize_superjob_vacancy

logger = logging.getLogger(__name__)


class SuperJobProvider(VacancyProvider):
    key = "superjob"
    title = "SuperJob"

    def __init__(
        self,
        api_url: str,
        header_factory: Callable[[Optional[str]], dict],
        token_factory: Optional[Callable[[], str]] = None,
        per_page: int = 20,
    ):
        self.api_url = api_url
        self.header_factory = header_factory
        self.token_factory = token_factory
        self.per_page = per_page

    @staticmethod
    def _normalize(raw: dict) -> dict:
        return normalize_superjob_vacancy(raw).as_mapping()

    def search(self, *, filters: VacancySearchFilters, page: int = 0) -> SearchResult:
        order_field = "payment" if filters.sort in {"salary_desc", "salary_asc"} else "date"
        order_direction = "asc" if filters.sort == "salary_asc" else "desc"
        params = {
            "keyword": filters.keyword,
            "period": filters.period_days,
            "order_field": order_field,
            "order_direction": order_direction,
            "count": self.per_page,
            "page": page,
        }
        if filters.salary_from is not None:
            params["payment_from"] = filters.salary_from
        if filters.salary_only:
            params["no_agreement"] = 1
        if filters.region.isdigit():
            params["town"] = filters.region

        try:
            # SuperJob vacancy search is public for listings themselves: the
            # application secret in X-Api-App-Id is sufficient. A user OAuth
            # token is optional and is reserved for user-specific methods
            # (resumes, contacts, applications). Keeping search independent of
            # the browser session lets SuperJob participate in unified search
            # and cross-source deduplication without forcing account login.
            token = self.token_factory() if self.token_factory else None
            response = requests.get(
                self.api_url,
                params=params,
                headers=self.header_factory(token),
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            items = [self._normalize(item) for item in payload.get("objects", [])]
            items = filter_vacancies(items, filters)
            total = int(payload.get("total", 0) or 0)
            return SearchResult(
                items=items,
                total=total,
                page=page,
                pages=(total + self.per_page - 1) // self.per_page if total else 0,
                has_next=bool(payload.get("more", False)),
            )
        except requests.RequestException:
            logger.exception("SuperJob vacancy search failed")
            return SearchResult(
                page=page,
                error="SuperJob временно не смог выполнить поиск.",
            )
        except (ValueError, TypeError, KeyError):
            logger.exception("SuperJob returned invalid vacancy payload")
            return SearchResult(
                page=page,
                error="SuperJob вернул некорректный ответ.",
            )
        except RuntimeError:
            logger.exception("SuperJob token preparation failed")
            return SearchResult(page=page, error="SuperJob временно недоступен.")

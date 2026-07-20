from __future__ import annotations

from typing import Callable

import requests

from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters


class SuperJobProvider(VacancyProvider):
    key = "superjob"
    title = "SuperJob"

    def __init__(self, api_url: str, header_factory: Callable[[str], dict], token_factory: Callable[[], str], per_page: int = 20):
        self.api_url = api_url
        self.header_factory = header_factory
        self.token_factory = token_factory
        self.per_page = per_page

    @staticmethod
    def _normalize(raw: dict) -> dict:
        town = raw.get("town") or {}
        return {
            "external_id": str(raw.get("id") or ""),
            "source": "superjob",
            "source_title": "SuperJob",
            "title": raw.get("profession") or "Без названия",
            "company": raw.get("firm_name") or "Компания не указана",
            "salary_from": raw.get("payment_from"),
            "salary_to": raw.get("payment_to"),
            "currency": (raw.get("currency") or "RUB").upper(),
            "location": town.get("title", "") if isinstance(town, dict) else str(town),
            "remote": bool(raw.get("is_remote_work")),
            "schedule": (raw.get("type_of_work") or {}).get("title", "") if isinstance(raw.get("type_of_work"), dict) else "",
            "employment": (raw.get("place_of_work") or {}).get("title", "") if isinstance(raw.get("place_of_work"), dict) else "",
            "description": raw.get("candidat") or raw.get("work") or "",
            "requirements": raw.get("experience", {}).get("title", "") if isinstance(raw.get("experience"), dict) else "",
            "published_at": raw.get("date_published") or "",
            "url": raw.get("link") or "",
        }

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

        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers=self.header_factory(self.token_factory()),
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            items = [self._normalize(item) for item in payload.get("objects", [])]
            if filters.remote_only:
                items = [item for item in items if item.get("remote")]
            total = int(payload.get("total", 0) or 0)
            return SearchResult(
                items=items,
                total=total,
                page=page,
                pages=(total + self.per_page - 1) // self.per_page if total else 0,
                has_next=bool(payload.get("more", False)),
            )
        except Exception as exc:
            return SearchResult(page=page, error=f"SuperJob: {exc}")

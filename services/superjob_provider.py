from __future__ import annotations

from typing import Callable

import requests

from .base_provider import SearchResult, VacancyProvider


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

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        try:
            response = requests.get(
                self.api_url,
                params={
                    "keyword": keyword,
                    "period": 7,
                    "order_field": "date",
                    "order_direction": "desc",
                    "count": self.per_page,
                    "page": page,
                },
                headers=self.header_factory(self.token_factory()),
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            items = [self._normalize(item) for item in payload.get("objects", [])]
            if remote_only:
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

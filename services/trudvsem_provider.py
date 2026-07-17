from __future__ import annotations

from typing import Any

import requests

from .base_provider import SearchResult, VacancyProvider


class TrudvsemProvider(VacancyProvider):
    key = "trudvsem"
    title = "Работа России"
    api_url = "https://opendata.trudvsem.ru/api/v1/vacancies"

    def __init__(self, user_agent: str, per_page: int = 20, timeout: int = 8):
        self.user_agent = user_agent
        self.per_page = per_page
        self.timeout = timeout

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def _normalize(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        raw = item.get("vacancy") or item
        if not isinstance(raw, dict):
            return None

        company = raw.get("company") or {}
        region = raw.get("region") or {}
        addresses = raw.get("addresses") or {}
        address = addresses.get("address") if isinstance(addresses, dict) else None
        if isinstance(address, list):
            address = ", ".join(
                self._text(x.get("location") if isinstance(x, dict) else x)
                for x in address if x
            )
        elif isinstance(address, dict):
            address = address.get("location") or address.get("address")

        schedule = self._text(raw.get("schedule"))
        employment = self._text(raw.get("employment"))
        remote_text = " ".join([schedule, employment, self._text(raw.get("work_places"))]).lower()

        requirements = raw.get("requirements") or {}
        qualification = requirements.get("qualification", "") if isinstance(requirements, dict) else ""
        description = raw.get("duty") or raw.get("job-description") or qualification
        requirements_text = (
            requirements.get("qualification") or requirements.get("education") or ""
            if isinstance(requirements, dict) else requirements
        )

        external_id = self._text(raw.get("id") or raw.get("vacancy-id"))
        url = self._text(raw.get("vac_url") or raw.get("url"))
        if not url and external_id:
            url = f"https://trudvsem.ru/vacancy/card/{external_id}"

        return {
            "external_id": external_id,
            "source": self.key,
            "source_title": self.title,
            "title": self._text(raw.get("job-name") or raw.get("name")) or "Без названия",
            "company": self._text(company.get("name") if isinstance(company, dict) else company) or "Компания не указана",
            "salary_from": raw.get("salary_min"),
            "salary_to": raw.get("salary_max"),
            "currency": self._text(raw.get("currency")) or "RUB",
            "location": self._text(region.get("name") if isinstance(region, dict) else region) or self._text(address),
            "remote": "дистан" in remote_text or "удален" in remote_text or "remote" in remote_text,
            "schedule": schedule,
            "employment": employment,
            "description": self._text(description),
            "requirements": self._text(requirements_text),
            "published_at": self._text(raw.get("creation-date") or raw.get("date")),
            "url": url,
        }

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        params = {
            "text": keyword,
            "limit": self.per_page,
            "offset": max(page, 0) * self.per_page,
        }
        try:
            response = requests.get(
                self.api_url,
                params=params,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("API вернул данные в неожиданном формате")

            total = int((payload.get("meta") or {}).get("total", 0) or 0)
            results = payload.get("results") or {}
            raw_items = results.get("vacancies") if isinstance(results, dict) else []
            if not isinstance(raw_items, list):
                raw_items = []

            items = []
            for raw_item in raw_items:
                normalized = self._normalize(raw_item)
                if normalized:
                    items.append(normalized)
            if remote_only:
                items = [item for item in items if item.get("remote")]

            pages = (total + self.per_page - 1) // self.per_page if total else 0
            return SearchResult(
                items=items,
                total=total,
                page=page,
                pages=pages,
                has_next=page + 1 < pages,
            )
        except Exception as exc:
            detail = ""
            response = getattr(exc, "response", None)
            if response is not None:
                detail = f" Ответ сервиса: {response.text[:300]}"
            return SearchResult(page=page, error=f"Работа России временно не отвечает: {exc}.{detail}")

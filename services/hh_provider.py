from __future__ import annotations

import logging
from typing import Callable

import requests

from .base_provider import SearchResult, VacancyProvider

logger = logging.getLogger(__name__)


class HeadHunterProvider(VacancyProvider):
    key = "hh"
    title = "HeadHunter"

    def __init__(
        self,
        api_url: str,
        header_factory: Callable[[str | None], dict],
        token_factory: Callable[[], str] | None = None,
        per_page: int = 20,
        timeout: int = 15,
    ):
        self.api_url = api_url
        self.header_factory = header_factory
        self.token_factory = token_factory
        self.per_page = per_page
        self.timeout = timeout

    @staticmethod
    def _normalize(raw: dict) -> dict:
        area = raw.get("area") or {}
        employer = raw.get("employer") or {}
        salary = raw.get("salary") or {}
        schedule = raw.get("schedule") or {}
        employment = raw.get("employment") or {}
        experience = raw.get("experience") or {}
        snippet = raw.get("snippet") or {}

        description_parts = [
            snippet.get("requirement") or "",
            snippet.get("responsibility") or "",
        ]
        description = " ".join(part for part in description_parts if part).strip()

        return {
            "external_id": str(raw.get("id") or ""),
            "source": "hh",
            "source_title": "HeadHunter",
            "title": raw.get("name") or "Без названия",
            "company": employer.get("name") or "Компания не указана",
            "salary_from": salary.get("from"),
            "salary_to": salary.get("to"),
            "currency": (salary.get("currency") or "").upper(),
            "location": area.get("name") or "",
            "remote": schedule.get("id") == "remote",
            "schedule": schedule.get("name") or "",
            "employment": employment.get("name") or "",
            "description": description,
            "requirements": experience.get("name") or "",
            "published_at": raw.get("published_at") or "",
            "url": raw.get("alternate_url") or raw.get("apply_alternate_url") or "",
        }

    def _request(self, params: dict, token: str | None) -> requests.Response:
        return requests.get(
            self.api_url,
            params=params,
            headers=self.header_factory(token),
            timeout=self.timeout,
        )

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        params = {
            "text": keyword,
            "period": 7,
            "page": page,
            "per_page": self.per_page,
            "order_by": "publication_time",
        }
        if remote_only:
            params["schedule"] = "remote"

        token = None
        if self.token_factory is not None:
            try:
                token = self.token_factory()
            except Exception as exc:
                logger.warning("HH token unavailable, using public search: %s", exc)

        try:
            response = self._request(params, token)

            # Поиск вакансий у HH публичный. Если пользовательский OAuth-токен
            # ограничен или отозван, повторяем запрос без Authorization.
            if token and response.status_code in {401, 403}:
                logger.warning(
                    "HH authenticated search returned %s; retrying public search",
                    response.status_code,
                )
                response = self._request(params, None)

            response.raise_for_status()
            payload = response.json()
            raw_items = payload.get("items", [])
            items = [self._normalize(item) for item in raw_items]

            return SearchResult(
                items=items,
                total=int(payload.get("found", 0) or 0),
                page=int(payload.get("page", page) or page),
                pages=int(payload.get("pages", 0) or 0),
                has_next=(int(payload.get("page", page) or page) + 1) < int(payload.get("pages", 0) or 0),
            )
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text[:1000] if exc.response is not None else ""
            logger.warning("HH vacancy search failed status=%s body=%s", status, body)
            message = f"HeadHunter: {exc}"
            if body:
                message += f" Ответ HH: {body}"
            return SearchResult(page=page, error=message)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("HH returned invalid vacancy payload: %s", exc)
            return SearchResult(page=page, error=f"HeadHunter: некорректный ответ API: {exc}")

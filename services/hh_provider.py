from __future__ import annotations

import logging
import os
from typing import Callable

import requests

from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters, canonical_currency

logger = logging.getLogger(__name__)
DEBUG_HH = os.environ.get("DEBUG_HH", "0").strip().lower() in {"1", "true", "yes", "on"}


def _safe_headers(headers: dict | None) -> dict:
    safe = {}
    for key, value in dict(headers or {}).items():
        if key.lower() == "authorization":
            safe[key] = "Bearer ***" if value else "***"
        else:
            safe[key] = value
    return safe


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

        description = " ".join(
            part
            for part in (
                snippet.get("requirement") or "",
                snippet.get("responsibility") or "",
            )
            if part
        ).strip()

        return {
            "external_id": str(raw.get("id") or ""),
            "source": "hh",
            "source_title": "HeadHunter",
            "title": raw.get("name") or "Без названия",
            "company": employer.get("name") or "Компания не указана",
            "salary_from": salary.get("from"),
            "salary_to": salary.get("to"),
            "currency": canonical_currency(salary.get("currency")),
            "location": area.get("name") or "",
            "remote": schedule.get("id") == "remote",
            "schedule": schedule.get("name") or "",
            "employment": employment.get("name") or "",
            "experience": experience.get("name") or "",
            "description": description,
            "requirements": experience.get("name") or "",
            "published_at": raw.get("published_at") or "",
            "url": raw.get("alternate_url") or raw.get("apply_alternate_url") or "",
        }

    def _request(self, params: dict, token: str | None, attempt: str) -> requests.Response:
        headers = self.header_factory(token)
        if DEBUG_HH:
            logger.info(
                "HH REQUEST attempt=%s method=GET endpoint=%s params=%s headers=%s",
                attempt,
                self.api_url,
                params,
                _safe_headers(headers),
            )

        response = requests.get(
            self.api_url,
            params=params,
            headers=headers,
            timeout=self.timeout,
        )

        if DEBUG_HH:
            logger.info(
                "HH RESPONSE attempt=%s status=%s url=%s request_headers=%s response_headers=%s body=%s",
                attempt,
                response.status_code,
                response.url,
                _safe_headers(response.request.headers),
                dict(response.headers),
                response.text[:2000],
            )
        return response

    def search(self, *, filters: VacancySearchFilters, page: int = 0) -> SearchResult:
        order_by = {
            "date": "publication_time",
            "salary_desc": "salary_desc",
            "salary_asc": "salary_asc",
            "relevance": "relevance",
        }.get(filters.sort, "publication_time")
        params = {
            "period": filters.period_days,
            "page": page,
            "per_page": self.per_page,
            "order_by": order_by,
        }
        if filters.keyword:
            params["text"] = filters.keyword
        if filters.work_format == "remote":
            params["schedule"] = "remote"
        elif filters.work_format == "hybrid":
            params["schedule"] = "flexible"
        hh_experience = {
            "no_experience": "noExperience",
            "between_1_and_3": "between1And3",
            "between_3_and_6": "between3And6",
            "more_than_6": "moreThan6",
        }.get(filters.experience)
        if hh_experience:
            params["experience"] = hh_experience
        if filters.employment:
            params["employment"] = filters.employment
        if filters.currency:
            params["currency"] = "RUR" if filters.currency == "RUB" else filters.currency
        if filters.salary_from is not None:
            params["salary"] = filters.salary_from
        if filters.salary_only:
            params["only_with_salary"] = "true"

        hh_region_ids = {
            "россия": "113",
            "москва": "1",
            "санкт-петербург": "2",
            "санкт петербург": "2",
            "екатеринбург": "3",
            "новосибирск": "4",
            "казань": "88",
            "нижний новгород": "66",
            "самара": "78",
            "омск": "68",
            "челябинск": "104",
            "ростов-на-дону": "76",
            "уфа": "99",
            "красноярск": "54",
            "пермь": "72",
            "воронеж": "26",
            "волгоград": "24",
            "краснодар": "53",
        }
        if filters.region:
            region_key = filters.region.casefold().strip()
            if region_key.isdigit():
                params["area"] = region_key
            elif region_key in hh_region_ids:
                params["area"] = hh_region_ids[region_key]

        token = None
        if self.token_factory is not None:
            try:
                token = (self.token_factory() or "").strip()
            except Exception as exc:
                logger.exception("HH application token unavailable")
                return SearchResult(
                    page=page,
                    error=f"HeadHunter: не удалось получить токен приложения: {exc}",
                )

        if not token:
            return SearchResult(
                page=page,
                error="HeadHunter: токен приложения HH_APP_TOKEN не настроен.",
            )

        try:
            response = self._request(params, token, "application")
            response.raise_for_status()
            payload = response.json()
            items = [self._normalize(item) for item in payload.get("items", [])]
            if filters.region and "area" not in params:
                region_query = filters.region.casefold()
                items = [item for item in items if region_query in str(item.get("location") or "").casefold()]
            if filters.work_format == "onsite":
                items = [item for item in items if not item.get("remote") and "гибк" not in str(item.get("schedule") or "").casefold()]
            if filters.currency:
                items = [item for item in items if canonical_currency(item.get("currency")) == filters.currency]
            current_page = int(payload.get("page", page) or page)
            pages = int(payload.get("pages", 0) or 0)

            return SearchResult(
                items=items,
                total=int(payload.get("found", 0) or 0),
                page=current_page,
                pages=pages,
                has_next=(current_page + 1) < pages,
            )
        except requests.RequestException as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text[:2000] if exc.response is not None else ""
            response_headers = dict(exc.response.headers) if exc.response is not None else {}
            logger.exception(
                "HH vacancy search failed status=%s response_headers=%s body=%s",
                status,
                response_headers,
                body,
            )
            message = f"HeadHunter: {exc}"
            if status in {401, 403}:
                message += " Токен приложения HH отклонён. Проверьте HH_APP_TOKEN в Render."
            if status == 403:
                request_id = response_headers.get("X-Request-Id") or response_headers.get("x-request-id")
                server = response_headers.get("Server") or response_headers.get("server")
                message += " Доступ отклонён на стороне HH или защитного шлюза."
                if server:
                    message += f" Server: {server}."
                if request_id:
                    message += f" Request ID: {request_id}."
            elif body:
                message += f" Ответ HH: {body}"
            return SearchResult(page=page, error=message)
        except (ValueError, TypeError, KeyError) as exc:
            logger.exception("HH returned invalid vacancy payload")
            return SearchResult(page=page, error=f"HeadHunter: некорректный ответ API: {exc}")

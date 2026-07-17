from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_provider import SearchResult, VacancyProvider

logger = logging.getLogger(__name__)


class TrudvsemProvider(VacancyProvider):
    key = "trudvsem"
    title = "Работа России"
    api_url = "https://opendata.trudvsem.ru/api/v1/vacancies"

    def __init__(self, user_agent: str, per_page: int = 50, timeout: tuple[int, int] = (4, 8)):
        self.user_agent = user_agent
        self.per_page = max(1, min(int(per_page), 100))
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=0,
            connect=0,
            read=0,
            backoff_factor=0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

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
                for x in address
                if x
            )
        elif isinstance(address, dict):
            address = address.get("location") or address.get("address")

        schedule = self._text(raw.get("schedule"))
        employment = self._text(raw.get("employment"))
        remote_text = " ".join(
            [schedule, employment, self._text(raw.get("work_places"))]
        ).lower()
        requirements = raw.get("requirements") or {}
        qualification = (
            requirements.get("qualification", "")
            if isinstance(requirements, dict)
            else ""
        )
        description = raw.get("duty") or raw.get("job-description") or qualification
        requirements_text = (
            requirements.get("qualification") or requirements.get("education") or ""
            if isinstance(requirements, dict)
            else requirements
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
            "company": self._text(
                company.get("name") if isinstance(company, dict) else company
            )
            or "Компания не указана",
            "salary_from": raw.get("salary_min"),
            "salary_to": raw.get("salary_max"),
            "currency": self._text(raw.get("currency")) or "RUB",
            "location": self._text(
                region.get("name") if isinstance(region, dict) else region
            )
            or self._text(address),
            "remote": (
                "дистан" in remote_text
                or "удален" in remote_text
                or "remote" in remote_text
            ),
            "schedule": schedule,
            "employment": employment,
            "description": self._text(description),
            "requirements": self._text(requirements_text),
            "published_at": self._text(raw.get("creation-date") or raw.get("date")),
            "url": url,
        }

    @staticmethod
    def _matches_keyword(item: dict[str, Any], keyword: str) -> bool:
        terms = [term.lower() for term in keyword.split() if term.strip()]
        if not terms:
            return True
        haystack = " ".join(
            str(item.get(field) or "")
            for field in ("title", "company", "location", "description", "requirements")
        ).lower()
        return all(term in haystack for term in terms)

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(
            self.api_url,
            params=params,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Connection": "close",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("API вернул данные в неожиданном формате")
        return payload

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        page = max(page, 0)
        base_params = {
            "limit": self.per_page,
            "offset": page * self.per_page,
        }

        # First try server-side text search. If the public service handles that
        # query slowly, retry without text and filter the returned page locally.
        attempts = []
        if keyword:
            attempts.append(({**base_params, "text": keyword}, False))
        attempts.append((base_params, bool(keyword)))

        errors: list[str] = []
        for params, local_filter in attempts:
            try:
                payload = self._request(params)
                meta = payload.get("meta") or {}
                total = int(meta.get("total", 0) or 0) if isinstance(meta, dict) else 0
                results = payload.get("results") or {}
                raw_items = results.get("vacancies") if isinstance(results, dict) else []
                if not isinstance(raw_items, list):
                    raw_items = []

                items = [item for raw in raw_items if (item := self._normalize(raw))]
                if local_filter:
                    items = [item for item in items if self._matches_keyword(item, keyword)]
                    # The API total describes all vacancies, not local matches.
                    total = len(items)
                if remote_only:
                    items = [item for item in items if item.get("remote")]
                    if local_filter:
                        total = len(items)

                pages = (total + self.per_page - 1) // self.per_page if total else 0
                return SearchResult(
                    items=items,
                    total=total,
                    page=page,
                    pages=pages,
                    has_next=(page + 1 < pages) if not local_filter else False,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                logger.warning("Trudvsem connection failed params=%s error=%s", params, exc)
                errors.append(f"соединение: {exc}")
            except requests.HTTPError as exc:
                response = exc.response
                status = response.status_code if response is not None else None
                body = response.text[:250] if response is not None else ""
                logger.warning(
                    "Trudvsem HTTP error params=%s status=%s body=%s",
                    params,
                    status,
                    body,
                )
                errors.append(f"HTTP {status or 'ошибка'}")
            except (ValueError, TypeError, KeyError) as exc:
                logger.warning("Trudvsem response parse failed params=%s error=%s", params, exc)
                errors.append(f"некорректный ответ: {exc}")

        return SearchResult(
            page=page,
            error=(
                "Сервис «Работа России» временно не отвечает. "
                "Попробуйте повторить поиск позже."
                + (f" Технические сведения: {'; '.join(errors)}" if errors else "")
            ),
        )

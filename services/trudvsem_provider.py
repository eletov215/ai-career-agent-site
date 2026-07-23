from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters

logger = logging.getLogger(__name__)

class TrudvsemProvider(VacancyProvider):
    key = "trudvsem"
    title = "Работа России"
    api_url = "https://opendata.trudvsem.ru/api/v1/vacancies"

    def __init__(
        self,
        user_agent: str,
        per_page: int = 25,
        timeout: tuple[int, int] = (5, 20),
        scan_pages: int = 1,
        request_attempts: int = 5,
        retry_backoff: float = 1.0,
    ):
        self.user_agent = user_agent
        self.per_page = max(1, min(int(per_page), 100))
        self.timeout = timeout
        self.scan_pages = max(1, min(int(scan_pages), 10))
        self.request_attempts = max(1, min(int(request_attempts), 10))
        self.retry_backoff = max(0.1, min(float(retry_backoff), 10.0))
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
        requirement = raw.get("requirement") or {}
        requirements_value = raw.get("requirements") or ""
        qualification = (
            requirement.get("qualification", "")
            if isinstance(requirement, dict)
            else ""
        )
        education = (
            requirement.get("education", "")
            if isinstance(requirement, dict)
            else ""
        )
        description = raw.get("duty") or raw.get("job-description") or qualification
        requirements_text = " ".join(
            part for part in (self._text(requirements_value), self._text(qualification), self._text(education)) if part
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
            "experience": self._text(raw.get("experience")) or self._text(raw.get("required_experience")),
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
        last_error: Exception | None = None

        for attempt in range(1, self.request_attempts + 1):
            try:
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

                # Повторяем только временные HTTP-ошибки. Ошибки клиента 4xx,
                # кроме 429, должны сразу попадать в журнал и завершать запрос.
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if 400 <= response.status_code < 500:
                    response.raise_for_status()

                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("API вернул данные в неожиданном формате")

                api_status = str(payload.get("status") or response.status_code)
                if api_status != "200":
                    meta = payload.get("meta") or {}
                    detail = meta.get("error") if isinstance(meta, dict) else None
                    raise ValueError(detail or f"API вернул статус {api_status}")

                if attempt > 1:
                    logger.info(
                        "Trudvsem request recovered attempt=%s offset=%s limit=%s",
                        attempt,
                        params.get("offset"),
                        params.get("limit"),
                    )
                return payload

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code not in {429, 500, 502, 503, 504}:
                    raise
            except requests.RequestException as exc:
                last_error = exc

            if attempt >= self.request_attempts:
                break

            delay = min(8.0, self.retry_backoff * (2 ** (attempt - 1)))
            logger.warning(
                "Trudvsem request failed; retrying attempt=%s/%s delay=%.1fs offset=%s limit=%s error=%s",
                attempt,
                self.request_attempts,
                delay,
                params.get("offset"),
                params.get("limit"),
                last_error,
            )
            time.sleep(delay)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Не удалось выполнить запрос к API 'Работы России'")



    def fetch_batch(
        self,
        *,
        offset: int = 0,
        limit: int = 1,
        modified_from: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load a small API batch for the background cache worker."""
        safe_limit = max(1, min(int(limit), 10))
        safe_offset = max(1, int(offset))

        params: dict[str, Any] = {
            "limit": safe_limit,
            "offset": safe_offset,
        }
        if modified_from:
            params["modifiedFrom"] = modified_from

        payload = self._request(params)

        logger.info(
            "TRUDVSEM RAW RESPONSE keys=%s",
            list(payload.keys()) if isinstance(payload, dict) else type(payload),
        )

        results = payload.get("results") or {}

        logger.info(
            "TRUDVSEM RESULTS TYPE=%s keys=%s",
            type(results).__name__,
            list(results.keys()) if isinstance(results, dict) else None,
        )

        raw_items = []

        if isinstance(results, dict):
            raw_items = results.get("vacancies") or []

            # Некоторые ответы API могут возвращать вакансии внутри вложенного объекта.
            if not raw_items and isinstance(results.get("vacancy"), list):
                raw_items = results.get("vacancy")

        if not isinstance(raw_items, list):
            logger.warning(
                "TRUDVSEM unexpected vacancies format type=%s",
                type(raw_items).__name__,
            )
            return []

        normalized = [
            item
            for raw in raw_items
            if (item := self._normalize(raw))
        ]

        logger.info(
            "TRUDVSEM normalized items=%s raw_items=%s",
            len(normalized),
            len(raw_items),
        )

        return normalized

    def search(
        self,
        *,
        filters: VacancySearchFilters,
        page: int = 0,
    ) -> SearchResult:
        """Prevent user-facing requests from calling the external API directly."""
        logger.error("Direct TrudvsemProvider.search() call blocked; use VacancyStore")
        return SearchResult(
            page=max(page, 0),
            error="Поиск «Работы России» доступен только из локального кэша.",
        )

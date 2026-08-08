from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


from .base_provider import SearchResult, VacancyProvider
from .search_filters import VacancySearchFilters
from .vacancy_normalizer import normalize_trudvsem_vacancy

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TrudvsemBatch:
    """One deterministic page of the Trudvsem change feed."""

    items: list[dict[str, Any]]
    offset: int
    limit: int
    total: int | None

    @property
    def returned(self) -> int:
        return len(self.items)

    @property
    def exhausted(self) -> bool:
        if self.total is not None:
            return self.offset * self.limit >= self.total
        return self.returned < self.limit


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
    def _normalize(item: Any) -> dict[str, Any] | None:
        normalized = normalize_trudvsem_vacancy(item) if isinstance(item, dict) else None
        return normalized.as_mapping() if normalized is not None else None

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



    @staticmethod
    def _meta_total(payload: dict[str, Any]) -> int | None:
        meta = payload.get("meta") or {}
        if not isinstance(meta, dict):
            return None
        try:
            return max(0, int(meta.get("total")))
        except (TypeError, ValueError):
            return None

    def fetch_page(
        self,
        *,
        offset: int = 1,
        limit: int = 10,
        modified_from: str | None = None,
        modified_to: str | None = None,
    ) -> TrudvsemBatch:
        """Load one API page with stable incremental-window metadata."""

        safe_limit = max(1, min(int(limit), 100))
        safe_offset = max(1, int(offset))
        params: dict[str, Any] = {
            "limit": safe_limit,
            "offset": safe_offset,
        }
        if modified_from:
            params["modifiedFrom"] = modified_from
        if modified_to:
            params["modifiedTo"] = modified_to

        payload = self._request(params)
        results = payload.get("results") or {}
        raw_items: list[Any] = []
        if isinstance(results, dict):
            raw_items = results.get("vacancies") or []
            if not raw_items and isinstance(results.get("vacancy"), list):
                raw_items = results.get("vacancy")
        if not isinstance(raw_items, list):
            logger.warning(
                "TRUDVSEM unexpected vacancies format type=%s",
                type(raw_items).__name__,
            )
            raw_items = []

        normalized = [
            item
            for raw in raw_items
            if (item := self._normalize(raw))
        ]
        total = self._meta_total(payload)
        logger.info(
            "TRUDVSEM page normalized offset=%s limit=%s items=%s raw_items=%s total=%s incremental=%s",
            safe_offset,
            safe_limit,
            len(normalized),
            len(raw_items),
            total,
            bool(modified_from or modified_to),
        )
        return TrudvsemBatch(
            items=normalized,
            offset=safe_offset,
            limit=safe_limit,
            total=total,
        )

    def fetch_batch(
        self,
        *,
        offset: int = 1,
        limit: int = 10,
        modified_from: str | None = None,
        modified_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Compatibility wrapper returning only normalized vacancy items."""

        return self.fetch_page(
            offset=offset,
            limit=limit,
            modified_from=modified_from,
            modified_to=modified_to,
        ).items


    def search(
        self,
        *,
        filters: VacancySearchFilters,
        page: int = 0,
    ) -> SearchResult:
        """Prevent user-facing requests from calling the external API directly."""
        del filters
        logger.error("Direct TrudvsemProvider.search() call blocked; use VacancyStore")
        return SearchResult(
            page=max(page, 0),
            error="Поиск «Работы России» доступен только из локального кэша.",
        )

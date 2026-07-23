from dataclasses import dataclass, field
from typing import Any

from .search_filters import VacancySearchFilters


@dataclass
class SearchResult:
    items: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    page: int = 0
    pages: int = 0
    has_next: bool = False
    error: str | None = None


class VacancyProvider:
    key = "base"
    title = "Источник"

    def search(self, *, filters: VacancySearchFilters, page: int = 0) -> SearchResult:
        raise NotImplementedError

from dataclasses import dataclass, field
from typing import Any


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

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        raise NotImplementedError

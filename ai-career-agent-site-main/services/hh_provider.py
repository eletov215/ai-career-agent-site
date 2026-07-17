from .base_provider import SearchResult, VacancyProvider


class HeadHunterProvider(VacancyProvider):
    key = "hh"
    title = "HeadHunter"

    def search(self, *, keyword: str, page: int = 0, remote_only: bool = False) -> SearchResult:
        return SearchResult(
            page=page,
            error="HeadHunter временно недоступен: API возвращает 403. Подключение аккаунта сохранено.",
        )

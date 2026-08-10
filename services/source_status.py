"""Safe user-facing source-state presentation for SEARCH-004.

The search page must not reduce every provider to a binary configured/not-configured
flag.  This module converts configuration, the latest bounded search result and the
Trudvsem cache lifecycle into a small public contract that never exposes exception
messages, response bodies, credentials or internal infrastructure instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence


class SourceStateCode(StrEnum):
    """Public state codes accepted by the vacancy-search UI."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    CACHED = "cached"
    AUTH_REQUIRED = "auth_required"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"


SOURCE_TITLES: dict[str, str] = {
    "trudvsem": "Работа России",
    "superjob": "SuperJob",
    "reed": "Reed.co.uk",
    "hh": "HeadHunter",
}


@dataclass(frozen=True, slots=True)
class SourceState:
    """A bounded source state safe to render in a public response."""

    key: str
    title: str
    state: str
    selectable: bool
    selected: bool
    label: str
    detail: str | None = None
    loaded: int = 0
    reported_total: int = 0
    auth_required_for_actions: bool = False

    @property
    def available(self) -> bool:
        """Compatibility alias used by existing Jinja templates."""

        return self.selectable

    @property
    def status_text(self) -> str:
        """Compatibility alias for older source-card markup."""

        return self.label

    @property
    def note(self) -> str | None:
        """Compatibility alias for older source-card markup."""

        return self.detail


def _summary_value(summary: Any, name: str, default: Any = None) -> Any:
    if summary is None:
        return default
    if isinstance(summary, Mapping):
        return summary.get(name, default)
    return getattr(summary, name, default)


def _safe_non_negative(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _cache_age_text(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "время обновления неизвестно"
    age = max(0, int(age_seconds))
    if age < 60:
        return "обновлено менее минуты назад"
    if age < 3600:
        return f"обновлено {age // 60} мин. назад"
    if age < 86400:
        return f"обновлено {age // 3600} ч. назад"
    return f"обновлено {age // 86400} дн. назад"


def _direct_source_state(
    key: str,
    *,
    configured: bool,
    selected: bool,
    summary: Any,
    requires_user_auth: bool,
    auth_required_for_actions: bool,
) -> SourceState:
    title = SOURCE_TITLES[key]
    if not configured:
        if requires_user_auth:
            return SourceState(
                key=key,
                title=title,
                state=SourceStateCode.AUTH_REQUIRED.value,
                selectable=False,
                selected=False,
                label="Требуется подключение",
                detail="Подключите площадку, чтобы включить её в поиск.",
                auth_required_for_actions=True,
            )
        return SourceState(
            key=key,
            title=title,
            state=SourceStateCode.TEMPORARILY_UNAVAILABLE.value,
            selectable=False,
            selected=False,
            label="Временно недоступен",
            detail="Источник сейчас не участвует в поиске.",
            auth_required_for_actions=auth_required_for_actions,
        )

    loaded = _safe_non_negative(_summary_value(summary, "loaded", 0))
    reported_total = _safe_non_negative(_summary_value(summary, "total", 0))
    has_error = bool(_summary_value(summary, "error"))

    if selected and summary is not None and has_error:
        return SourceState(
            key=key,
            title=title,
            state=SourceStateCode.DEGRADED.value,
            selectable=True,
            selected=True,
            label="Работает с ограничениями",
            detail=(
                "Источник не ответил на последний запрос. "
                "Результаты остальных площадок сохранены."
            ),
            loaded=loaded,
            reported_total=reported_total,
            auth_required_for_actions=auth_required_for_actions,
        )

    if selected and summary is not None:
        if loaded:
            detail = f"В текущий снимок загружено {loaded} вакансий."
        else:
            detail = "Поиск выполнен, подходящих вакансий в текущем запросе нет."
        return SourceState(
            key=key,
            title=title,
            state=SourceStateCode.AVAILABLE.value,
            selectable=True,
            selected=True,
            label="Поиск выполнен",
            detail=detail,
            loaded=loaded,
            reported_total=reported_total,
            auth_required_for_actions=auth_required_for_actions,
        )

    if auth_required_for_actions:
        detail = "Поиск доступен без входа; подключение понадобится для личных действий."
        label = "Поиск доступен без входа"
    else:
        detail = "Источник готов к поиску."
        label = "Доступен для поиска"
    return SourceState(
        key=key,
        title=title,
        state=SourceStateCode.AVAILABLE.value,
        selectable=True,
        selected=selected,
        label=label,
        detail=detail,
        loaded=loaded,
        reported_total=reported_total,
        auth_required_for_actions=auth_required_for_actions,
    )


def _trudvsem_source_state(
    *,
    selected: bool,
    summary: Any,
    cache_total: int,
    cache_age_seconds: int | None,
    cache_ttl_seconds: int,
    sync_enabled: bool,
    sync_running: bool,
    sync_queued: bool,
    last_run_failed: bool,
) -> SourceState:
    key = "trudvsem"
    title = SOURCE_TITLES[key]
    safe_total = _safe_non_negative(cache_total)
    loaded = _safe_non_negative(_summary_value(summary, "loaded", 0))
    reported_total = _safe_non_negative(_summary_value(summary, "total", safe_total))

    if safe_total > 0:
        stale = bool(
            cache_age_seconds is not None
            and cache_ttl_seconds > 0
            and int(cache_age_seconds) > int(cache_ttl_seconds)
        )
        parts = [f"Сохранено {safe_total} вакансий", _cache_age_text(cache_age_seconds)]
        if sync_running or sync_queued:
            parts.append("обновление выполняется в фоне")
        if last_run_failed:
            parts.append("последнее обновление не завершилось")
        elif stale:
            parts.append("данные могут быть устаревшими")

        degraded = last_run_failed or stale
        return SourceState(
            key=key,
            title=title,
            state=(
                SourceStateCode.DEGRADED.value
                if degraded
                else SourceStateCode.CACHED.value
            ),
            selectable=True,
            selected=selected,
            label=(
                "Доступен сохранённый кэш"
                if degraded
                else "Поиск по сохранённым данным"
            ),
            detail=" · ".join(parts) + ".",
            loaded=loaded,
            reported_total=reported_total,
        )

    if sync_running or sync_queued:
        return SourceState(
            key=key,
            title=title,
            state=SourceStateCode.DEGRADED.value,
            selectable=True,
            selected=selected,
            label="Данные загружаются",
            detail="Кэш пока пуст; обновление выполняется в фоне.",
            loaded=loaded,
            reported_total=reported_total,
        )

    if sync_enabled:
        return SourceState(
            key=key,
            title=title,
            state=SourceStateCode.DEGRADED.value,
            selectable=True,
            selected=selected,
            label="Кэш пока пуст",
            detail="Обновление будет поставлено в очередь при следующем поиске.",
            loaded=loaded,
            reported_total=reported_total,
        )

    return SourceState(
        key=key,
        title=title,
        state=SourceStateCode.TEMPORARILY_UNAVAILABLE.value,
        selectable=False,
        selected=False,
        label="Временно недоступен",
        detail="Сохранённых данных нет, фоновое обновление отключено.",
        loaded=loaded,
        reported_total=reported_total,
    )


def build_source_states(
    *,
    configured_sources: Mapping[str, bool],
    selected_sources: Sequence[str],
    source_results: Mapping[str, Any] | None = None,
    trudvsem_cache_total: int = 0,
    trudvsem_cache_age_seconds: int | None = None,
    trudvsem_cache_ttl_seconds: int = 0,
    trudvsem_sync_enabled: bool = True,
    trudvsem_sync_running: bool = False,
    trudvsem_sync_queued: bool = False,
    trudvsem_last_run_failed: bool = False,
    auth_required_sources: Sequence[str] = (),
) -> list[SourceState]:
    """Return all public source states in a stable UI order.

    ``auth_required_sources`` is intentionally generic for future providers.  HH
    and SuperJob public vacancy search remains available through app-level
    credentials; their user OAuth is represented only by
    ``auth_required_for_actions`` and does not disable the search checkbox.
    """

    selected = {str(value).strip() for value in selected_sources if str(value).strip()}
    summaries = source_results or {}
    auth_required = {
        str(value).strip() for value in auth_required_sources if str(value).strip()
    }

    states = [
        _trudvsem_source_state(
            selected="trudvsem" in selected,
            summary=summaries.get("trudvsem"),
            cache_total=trudvsem_cache_total,
            cache_age_seconds=trudvsem_cache_age_seconds,
            cache_ttl_seconds=trudvsem_cache_ttl_seconds,
            sync_enabled=trudvsem_sync_enabled,
            sync_running=trudvsem_sync_running,
            sync_queued=trudvsem_sync_queued,
            last_run_failed=trudvsem_last_run_failed,
        )
    ]
    for key in ("superjob", "reed", "hh"):
        states.append(
            _direct_source_state(
                key,
                configured=bool(configured_sources.get(key)),
                selected=key in selected,
                summary=summaries.get(key),
                requires_user_auth=key in auth_required,
                auth_required_for_actions=key in {"superjob", "hh"},
            )
        )
    return states


def selectable_source_keys(states: Sequence[SourceState]) -> set[str]:
    """Return source keys that may participate in a public search request."""

    return {state.key for state in states if state.selectable}

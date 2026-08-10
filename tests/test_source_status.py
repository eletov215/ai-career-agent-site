from __future__ import annotations

from services.source_status import (
    SourceStateCode,
    build_source_states,
    selectable_source_keys,
)


def _by_key(states):
    return {state.key: state for state in states}


def test_direct_provider_failure_is_degraded_without_raw_error_text():
    states = _by_key(
        build_source_states(
            configured_sources={"hh": True, "superjob": False, "reed": False},
            selected_sources=["hh"],
            source_results={
                "hh": {
                    "loaded": 0,
                    "total": 0,
                    "error": "secret provider response body and token",
                }
            },
            trudvsem_sync_enabled=False,
        )
    )

    hh = states["hh"]
    assert hh.state == SourceStateCode.DEGRADED.value
    assert hh.selectable is True
    assert hh.selected is True
    assert hh.label == "Работает с ограничениями"
    assert "secret" not in (hh.detail or "")
    assert "token" not in (hh.detail or "")


def test_trudvsem_fresh_cache_is_explicitly_cached_not_live_available():
    states = _by_key(
        build_source_states(
            configured_sources={"hh": False, "superjob": False, "reed": False},
            selected_sources=["trudvsem"],
            trudvsem_cache_total=102,
            trudvsem_cache_age_seconds=90,
            trudvsem_cache_ttl_seconds=3600,
            trudvsem_sync_enabled=True,
        )
    )

    trudvsem = states["trudvsem"]
    assert trudvsem.state == SourceStateCode.CACHED.value
    assert trudvsem.selectable is True
    assert trudvsem.label == "Поиск по сохранённым данным"
    assert "Сохранено 102 вакансий" in (trudvsem.detail or "")


def test_trudvsem_stale_or_failed_cache_is_degraded_but_selectable():
    states = _by_key(
        build_source_states(
            configured_sources={"hh": False, "superjob": False, "reed": False},
            selected_sources=["trudvsem"],
            trudvsem_cache_total=20,
            trudvsem_cache_age_seconds=7200,
            trudvsem_cache_ttl_seconds=3600,
            trudvsem_sync_enabled=True,
            trudvsem_last_run_failed=True,
        )
    )

    trudvsem = states["trudvsem"]
    assert trudvsem.state == SourceStateCode.DEGRADED.value
    assert trudvsem.selectable is True
    assert trudvsem.label == "Доступен сохранённый кэш"
    assert "последнее обновление не завершилось" in (trudvsem.detail or "")


def test_no_cache_and_disabled_sync_is_temporarily_unavailable():
    states = build_source_states(
        configured_sources={"hh": False, "superjob": False, "reed": False},
        selected_sources=["trudvsem"],
        trudvsem_cache_total=0,
        trudvsem_sync_enabled=False,
    )
    by_key = _by_key(states)

    assert by_key["trudvsem"].state == SourceStateCode.TEMPORARILY_UNAVAILABLE.value
    assert by_key["trudvsem"].selectable is False
    assert "trudvsem" not in selectable_source_keys(states)


def test_auth_required_state_is_supported_for_future_user_only_source():
    states = _by_key(
        build_source_states(
            configured_sources={"hh": False, "superjob": False, "reed": False},
            selected_sources=["reed"],
            trudvsem_sync_enabled=False,
            auth_required_sources=["reed"],
        )
    )

    reed = states["reed"]
    assert reed.state == SourceStateCode.AUTH_REQUIRED.value
    assert reed.selectable is False
    assert reed.label == "Требуется подключение"


def test_public_hh_search_remains_available_without_user_oauth():
    states = _by_key(
        build_source_states(
            configured_sources={"hh": True, "superjob": True, "reed": True},
            selected_sources=[],
            trudvsem_sync_enabled=False,
        )
    )

    assert states["hh"].state == SourceStateCode.AVAILABLE.value
    assert states["hh"].selectable is True
    assert states["hh"].auth_required_for_actions is True
    assert states["hh"].label == "Поиск доступен без входа"
    assert states["superjob"].label == "Поиск доступен без входа"
    assert states["reed"].label == "Доступен для поиска"

# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Более новый ZIP текущего чата становится рабочей основой.
3. Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4. Главный entrypoint — `app.py`, WSGI — `app:app`; `app_fixed.py` не используется.

## 2. Текущий пакет

```text
SEARCH-004 — НУЖНА ПРОВЕРКА
branch: search-004-canonical-vacancies
commit: search: make vacancies route canonical and expose safe source states
production revision: 20260809_0007 (без новой migration)
```

## 3. Обязательный цикл

```text
актуальный ZIP + canonical docs
→ один package ID
→ inventory/risks/rollback
→ code + tests
→ branch/PR
→ green GitHub Actions
→ Render/API/E2E smoke
→ final status/docs
```

## 4. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra migrations
python -m pytest -q
python -m alembic check
```

GitHub Actions должен отдельно выполнить `Verify SEARCH-004 canonical route and source-state controls`, PostgreSQL migration/integration, backup/restore, Docker build/runtime и полный pytest.

## 5. SEARCH-004 production verification

1. `/health/ready` показывает revision `20260809_0007`.
2. `/vacancies` возвращает 200 и полный search UI.
3. `/vacancies/internal?<query>` возвращает 308 на `/vacancies` с тем же raw query.
4. Повторяющиеся `source`, `snapshot` и `page` не теряются.
5. Generated forms/pagination/navbar/home CTA не содержат `/vacancies/internal`.
6. Trudvsem показан как cached/degraded; HH/SuperJob/Reed — как live available/degraded/unavailable.
7. Ошибка одного provider не ломает общую страницу и не выводит traceback/body/token/env name.

## 6. Неприкосновенные правила

- `.env`, credentials, databases, dumps, backups, virtualenv, caches и bytecode не включаются в ZIP/GitHub.
- Реальные APIs в CI mocked.
- Production schema меняет только Alembic.
- SEARCH-004 не меняет SEARCH-003 snapshot schema/algorithm, SEARCH-002 thresholds, OAuth strategy или AI matching.
- Admin source telemetry остаётся SEARCH-005.

## 7. Rollback

Application revert и redeploy. Database revision `0007` сохраняется; downgrade не нужен. Legacy route должен оставаться доступным либо redirect-safe на rollback window.

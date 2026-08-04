# Changelog

Все значимые изменения проекта фиксируются в этом файле.

## Unreleased — DATA-001 (04 августа 2026)

### Added

- SQLAlchemy 2 runtime и единый `DatabaseRuntime`.
- PostgreSQL через Psycopg 3 и нормализация Render URL.
- Alembic и первая миграция `20260804_0001`.
- Модели текущих таблиц `accounts`, `hh_accounts`, `vacancies`.
- Команды `scripts/manage_db.py upgrade/current/check`.
- Необязательный `scripts/import_legacy_sqlite.py`.
- Тесты миграций, legacy adoption, URL-конфигурации, импорта и реального PostgreSQL round-trip.
- Документ `docs/DATABASE_MIGRATION.md`.

### Changed

- `app.py` использует SQLAlchemy для OAuth accounts.
- `VacancyStore` переведён с прямого `sqlite3` на SQLAlchemy с сохранением прежнего API.
- `/health` проверяет базу и возвращает backend/persistence/revision без credentials.
- Render start command выполняет Alembic migration перед Gunicorn.
- CI применяет миграции к SQLite и отдельному PostgreSQL 17 service container, выполняет `alembic check`, PostgreSQL persistence round-trip и использует актуальные версии GitHub Actions.

### Compatibility

- Без `DATABASE_URL` сохраняется SQLite fallback в `<DATA_DIR>/app.db`.
- Существующая SQLite schema может быть принята первой миграцией без удаления строк.
- Production считается переведённым только после подключения PostgreSQL и проверки persistence.

### Status

- `FND-001` — ВЫПОЛНЕНО.
- `FND-002` — ВЫПОЛНЕНО; Render подтверждён после `HH_CURRENCY_SCAN_PAGES=20`.
- `DATA-001` — НУЖНА ПРОВЕРКА.

## 03 августа 2026 — FND-002

- Добавлен `config.py` и режимы `production/development/test`.
- Централизована валидация переменных окружения.
- Провайдер HH получает debug/scan settings через конструктор.
- Добавлены startup/config tests.
- GitHub Actions и Render deploy подтверждены пользователем.

## 03 августа 2026 — FND-001

- Добавлены pytest infrastructure, route/provider/unit tests.
- Добавлен GitHub Actions workflow.
- Проверены намеренно красный и повторно зелёный CI.
- Подтверждён Render smoke deploy.

## Ранее

История интерфейсных, OAuth-, поиска и конструктора изменений сохранена в Git и предыдущих проектных материалах. Канонический текущий статус находится в `PLAN_CURRENT`.

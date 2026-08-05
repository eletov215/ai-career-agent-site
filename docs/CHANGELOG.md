# Changelog

## Unreleased — SEC-001 (05 августа 2026)

### Added

- `security.py` with Flask-WTF CSRF, Flask-Limiter, ProxyFix, request resource limits, neutral errors and browser security headers.
- CSP nonce contract for every script tag and static tests that forbid unprotected scripts/POST forms/inline event handlers.
- Secure session policy, production `SameSite=Lax`, OAuth state TTL/one-time consumption for success and error callbacks, and POST-only logout.
- Public sanitized Trudvsem status endpoint and header-secret diagnostics gate.
- PDF page/text limits and safe upload filename normalization.
- University-logo SSRF hardening: private-host/credentials/port rejection, validated redirects, bounded bodies and image signature checks.
- `docs/SECURITY.md`, security route/config/template/SSRF tests and an explicit CI step `Verify SEC-001 security controls`.
- Root `.gitignore` for secrets, databases, dumps, caches and virtual environments.

### Changed

- Technical `/debug/*` and detailed `/trudvsem/status` now return 404 unless diagnostics are explicitly enabled and authenticated by `X-Diagnostics-Secret`.
- Production `/trudvsem/refresh` is hidden; machine sync remains CSRF-exempt only behind `X-Sync-Secret`.
- Vacancy UI polls `/api/sources/trudvsem/status`, which excludes raw errors and persisted internal state.
- OAuth/provider error details are no longer reflected to users; callback state is validated before provider-controlled error fields; token-refresh network errors are converted to neutral messages; HH logs no longer include response bodies or complete response headers.
- Existing POST forms and JavaScript API calls now carry CSRF tokens; logout changed from GET to POST.
- Production configuration rejects insecure OAuth redirect URIs, `SameSite=Strict` (incompatible with external OAuth return), and disabled baseline controls.
- `requirements.txt` adds `Flask-WTF==1.3.0` and `Flask-Limiter==4.1.1`.

### Compatibility and status

- No database migration; Alembic revision remains `20260804_0002`.
- Existing templates/design and business flows are preserved, but all existing browser sessions are intentionally replaced by the new `aca_session` cookie.
- `SEC-001` is **НУЖНА ПРОВЕРКА** until GitHub Actions and Render smoke/security headers/CSRF/rate-limit/OAuth checks are confirmed.
- After confirmation, the next package is `OPS-001`; `DOMAIN-001` remains after OPS-001.

## 05 августа 2026 — DATA-002 COMPLETE 1.2.7

- GitHub Actions полностью зелёный, включая PostgreSQL migrations, integration test и полный pytest.
- Render `/health` подтвердил PostgreSQL и Alembic revision `20260804_0002`.
- Поиск вакансий работает в production без HTTP 500.
- `/trudvsem/status` возвращает secret-free `persisted_run`.
- После restart сохранились `cached_total=23`, `current_offset=30`, `last_processed=30`, `last_saved=30`, `last_started` и persisted run.
- `DATA-002` переведён в **ВЫПОЛНЕНО**; `SEC-001` переведён в **ГОТОВО К СТАРТУ**.
- Production-код в этом документальном обновлении не менялся.

## Unreleased — DATA-002 (04 августа 2026)

### Added

- Immutable domain records `UserRecord`, `OAuthConnectionRecord`, `VacancyRecord`, `SourceRecord` и `SyncRunRecord` в `domain/`.
- Models `User`, `OAuthConnection`, canonical `Vacancy`, `VacancySourceRecord`, and `SyncRun`.
- Repository layer for users, OAuth connections, canonical/source vacancies and sync runs.
- `services/storage.py` as the single persistence entry point used by `app.py`.
- Alembic revision `20260804_0002` with legacy OAuth copy and vacancy canonical/source migration.
- Persistent Trudvsem sync lifecycle records.
- Repository, relationship, architecture-boundary, legacy-adoption, and PostgreSQL integration tests.
- `docs/DOMAIN_MODEL.md`.

### Changed

- `app.py` no longer imports SQLAlchemy, ORM models or concrete repositories; it receives repositories through `StorageServices`.
- Current HH/SuperJob routes read unified `oauth_connections`; writes are transactionally mirrored to legacy provider tables during verification for rollback safety.
- `VacancyStore` delegates SQL queries to `VacancyRepository`.
- `/trudvsem/status` exposes the latest secret-free `persisted_run` when available.
- Legacy importer writes to the unified schema.
- CI compiles/tests `domain/`, `repositories/` and storage boundaries; PostgreSQL integration migrates seeded revision `0001` rows and validates source-record sequence continuity.

### Compatibility

- Legacy `accounts` and `hh_accounts` remain temporarily and receive mirrored HH/SuperJob writes for controlled application rollback.
- Existing source vacancy rows are copied without losing IDs/raw JSON/search fields.
- Current UI, routes, OAuth callbacks, search payloads, and `app:app` remain unchanged.

### Status

- `FND-001` — ВЫПОЛНЕНО.
- `FND-002` — ВЫПОЛНЕНО.
- `DATA-001` — ВЫПОЛНЕНО.
- `DATA-002` — ВЫПОЛНЕНО: CI, Render revision `20260804_0002`, production search и restart persistence подтверждены.
- `DOMAIN-001` подтверждён как отдельный будущий пакет после `SEC-001`/`OPS-001`; он не был потерян и не объединён с DATA-002.

Все значимые изменения проекта фиксируются в этом файле.

## 04 августа 2026 — DATA-001 CI fix 1.2.3

- Исправлен `tests/test_routes.py::test_sqlalchemy_account_storage_round_trip`: прямой вызов session-dependent helpers теперь выполняется внутри Flask request context.
- Production-код, OAuth-схема и модели базы не изменялись.
- GitHub Actions усилен отдельным обязательным PostgreSQL integration step и полным отчётом о skipped/xfail tests.
- Статус `DATA-001` остаётся **НУЖНА ПРОВЕРКА** до повторного зелёного CI и проверки PostgreSQL на Render.

## 04 августа 2026 — DOC-SYNC 1.2.1

- Исправлена рассинхронизация экспортированных PLAN_CURRENT DOCX/PDF.
- `FND-001` и `FND-002` зафиксированы как **ВЫПОЛНЕНО**.
- `DATA-001` остаётся **НУЖНА ПРОВЕРКА** до production PostgreSQL/persistence-проверки.
- Паспорт обновлён до версии 2.1, связанный план — 1.2.1.

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

## 2026-08-04 — Documentation cache-safe reissue

- PLAN_CURRENT updated to v1.2.2.
- FND-001 and FND-002 are confirmed as COMPLETED.
- DATA-001 remains NEEDS VERIFICATION.
- Versioned document filenames are used to prevent stale mobile/PDF cache confusion.

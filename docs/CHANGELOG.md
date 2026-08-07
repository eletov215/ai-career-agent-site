# AI Career Agent — журнал изменений

## 1.4.1 — 2026-08-07 — SYNC-001 candidate

### Добавлено

- external `TrudvsemSyncService`, long-running worker и one-shot/queue CLI;
- durable idempotent queue на `sync_runs`;
- `sync_workers` heartbeat model/repository;
- PostgreSQL advisory lock и SQLite lockfile;
- migration `20260807_0003` с one-active-run partial unique index;
- Render staging supervisor `scripts/start_runtime.py`;
- Docker Compose `sync-worker` profile;
- SYNC-001 unit/migration/config/manifest/route tests и отдельный CI step;
- `SYNC001_RUNBOOK.md` и `SYNC001_VERIFICATION_STATUS.md`.

### Изменено

- `app.py` больше не создаёт daemon thread и не выполняет Trudvsem provider HTTP;
- search/cache-miss/refresh/machine endpoint только создают persisted queued run;
- expected Alembic revision обновлена до `20260807_0003`;
- Render Start Command использует runtime supervisor;
- repository docs синхронизированы с PLAN_CURRENT 1.4.1 и passport 2.15.

### Совместимость и статус

- UI, search payload, OAuth и vacancy schema совместимы;
- существующий cache сохраняется при upstream failure;
- `SYNC-001 — НУЖНА ПРОВЕРКА НА GITHUB/RENDER`;
- после подтверждения следующий пакет — `SYNC-002`;
- real VPS по-прежнему отложен до предрелизного `INFRA-001`.

---

## 1.4.0 — 2026-08-07 — hosting-independent sequence

- кодовая инфраструктурная подготовка классифицирована как выполненный `INFRA-PREP-001`;
- real VPS test перенесён в pre-release window;
- OPS-001 закрыт как базовый пакет, production restore drill перенесён в OPS-002/REL-001;
- SYNC-001 выбран следующим кодовым пакетом.

---

## 1.3.5 — 2026-08-06 — INFRA-001

### Добавлено

- multi-target `Dockerfile`: non-root `runtime` и отдельный `ops` target с PostgreSQL 17 client tools;
- `compose.yaml`: private PostgreSQL, one-shot migrations, web, optional Caddy TLS, OPS и isolated restore-test profiles;
- единая Gunicorn policy в `infra/gunicorn.conf.py`;
- secret-free VPS templates в `infra/vps/`;
- `infra_probe.py` с JSON/Markdown report, DNS/TCP/TLS/HTTP checks и strict mode;
- manifest/document validators и container smoke script;
- INFRA unit/manifest/document tests и GitHub Actions build/smoke;
- DOC-STD-001 и единый формат PLAN_CURRENT, паспорта, runbooks и отчётов.

### Статусы

- `SEC-001 — ВЫПОЛНЕНО`;
- `OPS-001 — НУЖНА ФИНАЛЬНАЯ ПРОВЕРКА`;
- `INFRA-001 — НУЖНА ПРОВЕРКА НА VPS`.

---

## Unreleased — SEC-001 rate-limit fix 1.3.2 (06 августа 2026)

### Fixed

- Flask-Limiter больше не использует меняющийся адрес промежуточного Render proxy как bucket key.
- Добавлено валидируемое определение реального клиента: `CF-Connecting-IP`, затем первый адрес `X-Forwarded-For`, и только при явном `TRUST_PROXY_HEADERS=1`; без доверенного proxy заголовки игнорируются.
- Limiter storage key теперь содержит HMAC-SHA256 fingerprint адреса, а не исходный IP.
- `ProxyFix` доверяет только forwarded protocol (`x_proto=1`) и не переписывает `REMOTE_ADDR` по неоднозначной proxy-цепочке.
- Добавлен secret-free `GET /api/security/rate-limit-probe` с лимитом `5 per minute` для однозначной production-проверки HTTP 429.
- Добавлены regression tests для rotating proxy hops, CF/XFF fallback, spoof protection и `Retry-After`; SEC-001 CI step расширен новым тестовым модулем.

### Compatibility and status

- OPS-001 observability/backup code сохранён без отката.
- Database migration отсутствует; revision остаётся `20260804_0002`.
- `SEC-001` имеет статус **НУЖНА ПОВТОРНАЯ ПРОВЕРКА НА RENDER** до зелёного CI и получения `429` на probe endpoint.
- `OPS-001` остаётся **НУЖНА ПРОВЕРКА**.

## Unreleased - OPS-001 (05 августа 2026)

### Added

- `observability.py`: JSON/text stdout logging, secret/query/body redaction, `X-Request-ID`, bounded HTTP/provider metrics, recent sanitised errors and optional HTTPS alert queue.
- `/health/live` and `/health/ready`; `/health` remains a readiness alias.
- Diagnostics-only `/ops/status` and `/ops/alerts/test`.
- `operations/backup.py` with PostgreSQL custom-format backup, AES-256-GCM encryption, manifest/SHA-256 verification, controlled restore and row-count/revision validation.
- CLI scripts `backup_database.py`, `verify_backup.py`, `restore_database.py`, `send_test_alert.py`.
- `docs/OPERATIONS.md`, `docs/BACKUP_RESTORE.md`, `docs/INCIDENT_RESPONSE.md`.
- Tests for logging redaction, correlation IDs, readiness, metrics, alerts, encrypted backup/restore, tamper detection and production guards.
- GitHub Actions steps for OPS controls and real encrypted PostgreSQL backup/restore into a separate database.

### Changed

- `render.yaml` health path is `/health/ready`; non-secret log defaults are configured.
- Vacancy-provider searches, Trudvsem batches and university-logo lookup emit bounded provider metrics without user query/payload.
- Generic 500 handling emits a structured error event while keeping the response neutral.
- Repository hygiene rejects dump/backup/SQL/encrypted backup artifacts; missing root `.gitignore` restored.
- Embedded plan/passport/source-audit documents synchronised with canonical 1.3.x strategy.

### Compatibility and status

- No database migration; revision remains `20260804_0002`.
- No new mandatory variables for normal web startup. Alert webhook and backup encryption key are opt-in operational secrets.
- Local available tests pass; full Flask/PostgreSQL/backup verification is delegated to GitHub Actions.
- `OPS-001` is **НУЖНА ПРОВЕРКА** until CI, production health/log smoke, alert delivery and a real restore drill are confirmed.
- `SEC-001` remains **НУЖНА ПРОВЕРКА НА RENDER**; its GitHub security step is already green.

## Unreleased — SEC-001 (05 августа 2026)

### CI verification

- The repeated GitHub Actions run is fully green; `Verify SEC-001 security controls` passed 74 tests.
- SEC-001 still requires production smoke on Render from an accessible network.

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
- `SEC-001` is **НУЖНА ПРОВЕРКА НА RENDER**: GitHub Actions is confirmed; Render smoke/security headers/CSRF/rate-limit/OAuth checks remain.
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

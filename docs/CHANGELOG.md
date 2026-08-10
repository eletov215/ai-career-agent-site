# Changelog

## Unreleased — SEARCH-004 candidate (10 августа 2026)

### Added

- Canonical public vacancy route `/vacancies`.
- Safe `SourceState` contract: `available`, `cached`, `degraded`, `auth_required`, `temporarily_unavailable`.
- Explicit cached/degraded Trudvsem presentation and neutral live-provider state copy.
- SEARCH-004 route/source-state tests and dedicated GitHub Actions gate.
- Canonical metadata for the vacancy page.

### Changed

- `/vacancies/internal` is now a permanent method-preserving compatibility redirect that preserves the raw query string, repeated sources, SEARCH-003 snapshot ID and page.
- Main/compact forms, pagination and generated navigation URLs use `/vacancies`.
- Source cards and result summaries show safe user-facing state rather than binary availability.
- Provider failures no longer expose technical exception text or environment variable names in public UI.
- Explicitly requested but unavailable providers are removed before the SEARCH-003 aggregator and reported with neutral user copy.

### Verification status

- Python compile and Jinja parse: passed.
- Focused `tests/test_source_status.py`: 6 passed.
- Full available pytest: 193 passed, 6 skipped.
- GitHub Flask/PostgreSQL/Docker and Render canonical-route/source-state smoke: pending.

### Compatibility and rollback

- No database migration; production revision remains `20260809_0007`.
- Application revert is sufficient; legacy route remains redirect-safe.

## Unreleased — SEARCH-003 candidate (09 августа 2026)

### Added

- Persistent bounded `SearchSnapshot`/source/candidate/item schema and repository.
- Alembic revision `20260809_0007`.
- `SearchAggregationService` with per-provider cursor state, progressive bounded coverage, deterministic sort and committed page prefix.
- Honest `provider_reported_total` / `known_unique_total` / `total_is_exact` semantics.
- Secret-free `/health/search-pagination?snapshot=<uuid>`.
- SEARCH-003 route/migration/restart/failure/TTL/late-arrival tests and dedicated GitHub Actions gate.
- Same-provider anonymous publications now require a real external ID/URL for identity collapse; semantic fingerprints are reserved for conservative cross-source comparison.

### Changed

- `/vacancies/internal` pagination now carries an opaque snapshot ID.
- Canonical filter + SEARCH-002 dedup run before stable ordinal/page slicing.
- Approximate provider totals are no longer presented as exact unique totals.
- Render/Compose/VPS templates include bounded snapshot policy defaults.
- Backup inventory and PostgreSQL integration cover snapshot tables.

### Production hotfix — SEARCH-003 latency

- Первый Render smoke после revision `20260809_0007` выявил неприемлемую длительность первого поиска: candidate persistence выполняла SELECT на каждую вакансию, а default policy могла делать до трёх последовательных provider rounds в одном HTTP request.
- Candidate/source persistence переведена на batch lookup + bulk insert; materialized items записываются bulk insert.
- Повторная полная перезапись materialized rows при commit boundary удалена: commit обновляет только snapshot metadata.
- Добавлен отдельный логический `SEARCH_PAGE_SIZE=20`; `VACANCY_PAGE_SIZE=60` остаётся provider/cache page size.
- `SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST` default снижен `3 -> 1`, поэтому snapshot расширяется постепенно между переходами по страницам.
- Migration не меняется: production schema остаётся `20260809_0007`.

### Verification status

- Local compile and full available pytest: 182 passed, 6 skipped.
- SEARCH-003 focused suite: 18 passed.
- SQLite migration `0006 -> 0007 -> 0006 -> 0007` and Alembic check: passed.
- GitHub Actions and Render cross-page/restart smoke: passed; SEARCH-003 complete.

### Scope exclusions

- `/vacancies` route redesign is implemented in SEARCH-004 candidate.
- SEARCH-002 thresholds and OAuth strategy are unchanged.
- Exact total is not obtained by synchronous full upstream scan.

## Unreleased — SEARCH-002 (09 августа 2026)

### Added

- `services/vacancy_deduplication.py`: versioned strict fingerprint, conservative similarity and complete-link grouping.
- Explainability fields, deterministic primary card and retained multi-provider source list.
- Persistence exact-match grouping: one canonical `Vacancy`, multiple `VacancySourceRecord`, reversible split после изменения source publication.
- Multi-source card UI with stacked logos and expandable provider links.
- Dedicated SEARCH-002 tests and GitHub Actions gate.
- SEARCH-002 implementation, verification, runbook and dedup reference documents.
- Browser-readable aggregate verification endpoint `/health/search-dedup` for the latest completed search page; it exposes only counts/source names and never calls providers itself.

### Changed

- SuperJob vacancy search no longer depends on a browser OAuth session: public vacancy listings use the application `X-Api-App-Id` credential, while OAuth remains reserved for user-specific SuperJob features. This makes SuperJob available in unified search and SEARCH-002 live dedup smoke without forcing account login.
- Search aggregation applies dedup after canonical filters and before global sort/presentation.
- Additive Alembic revision `20260809_0006` adds nullable `dedup_key`/`dedup_version` columns and non-unique lookup indexes.
- Presenter and save key support merged cards.
- PLAN_CURRENT, passport, README, ROADMAP and source audit synchronized to 1.4.7/2.21.

### Security and compatibility

- Additional provider links accept only public HTTP/HTTPS URLs without credentials.
- Same-provider different IDs, different seniority/location/canonical codes and incompatible salary ranges are not merged.
- Candidate database revision is `20260809_0006`; application rollback may leave additive columns, controlled downgrade requires backup.

### Verification status

- Focused SEARCH-002/persistence/presenter tests: passed.
- SEARCH-002 dedup/migration suite: 15 passed; presenter suite: 5 passed; available regression groups passed.
- GitHub PostgreSQL/CI and Render multi-source smoke: pending.

### Scope exclusions

- Global pagination/sort/total after dedup remains SEARCH-003.
- Fuzzy company aliases, embeddings and ML merge are not used.

## 1.4.6 — 2026-08-08 — SEARCH-001 complete

- Green GitHub Actions confirmed SEARCH-001 contract/migration/regression gates.
- Render `/health/ready` confirmed revision `20260808_0005`.
- Production filters and cards passed smoke without HTTP 500.
- SEARCH-002 became the next package.

## Unreleased — SEARCH-001 (08 августа 2026)

### Added

- Typed `NormalizedVacancy` contract and canonical enums.
- Central vacancy normalizer for text, currency, salary and UTC dates.
- Provider adapters for HH, Reed, SuperJob and Trudvsem.
- Additive Alembic revision `20260808_0005` with canonical code columns/indexes.
- Exact common filters and legacy compatibility fallback.
- SEARCH-001 contract/migration tests and dedicated GitHub Actions gate.
- DOC-STD-001 v1.1 and uniform canonical document generator/template.

### Changed

- Store/repository/presenter use canonical fields rather than repeated provider-specific heuristics.
- `app.py` applies common filter policy after provider aggregation.
- README, ROADMAP, PLAN_CURRENT, passport and source audit synchronized to 1.4.5/2.19.

### Verification status

- Local focused tests: 29 passed.
- Full available pytest: 139 passed, 6 skipped.
- SQLite migration upgrade/check/downgrade/re-upgrade: passed.
- GitHub PostgreSQL/CI and Render revision/search smoke: pending.

### Scope exclusions

- Cross-source dedup remains SEARCH-002.
- Global pagination/total remains SEARCH-003.

## 1.4.3 — 2026-08-07 — SYNC-002 candidate

### Добавлено

- migration `20260807_0004` с `sync_checkpoints` и lifecycle fields source records;
- persistent committed watermark, bounded pending window и continuation offset/total;
- Trudvsem `modifiedFrom`/`modifiedTo` page adapter и provider lifecycle mapping;
- resumable bootstrap последних TTL-дней и incremental change-set across runs/reconnect;
- idempotent active/closed upsert, TTL closure, retention purge и reactivation;
- persistent bounded exponential retry/backoff без потери cache;
- checkpoint table в encrypted backup inventory;
- отдельный CI step и SYNC-002 implementation/verification/runbook docs.

### Изменено

- expected Alembic revision candidate — `20260807_0004`;
- diagnostics включают checkpoint, active/closed totals и retry state;
- worker не возвращает failure exit code при transient upstream error в long-running mode;
- VPS/Compose/Render templates содержат явные incremental/cleanup defaults;
- repository docs синхронизированы с PLAN_CURRENT 1.4.3 и passport 2.17.

### Проверки и статус

- локально: `130 passed, 6 skipped`; SYNC-002 tests — 8 passed;
- migration upgrade/downgrade/upgrade и Alembic check пройдены;
- `SYNC-002 — НУЖНА ПРОВЕРКА` до GitHub Actions и Render revision/checkpoint/cleanup smoke;
- после подтверждения следующий пакет — `SEARCH-001`.

---

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

# AI Career Agent — архитектура проекта

> Последнее обновление: 07 августа 2026 года  
> Текущий пакет: `SYNC-001` — external Trudvsem worker  
> Статус пакета: **НУЖНА ПРОВЕРКА НА GITHUB/RENDER**; expected revision `20260807_0003`

## 1. Цель архитектуры

```text
аккаунт -> карьерный профиль -> анализ резюме -> поиск вакансий
-> объяснимое совпадение -> письмо -> трекер откликов
```

Инфраструктура не должна быть жёстко привязана к Render. После выявленной недоступности Render из части сетей РФ Render остаётся staging/резервной площадкой. Production-кандидат выбирается в `INFRA-001`, затем подготавливается в `HOST-001`; собственный домен подключается до `MIG-001`. Тот же application code должен переноситься без изменения бизнес-логики.

## 2. Технологический стек

- Python 3.11, Flask 3.1.3, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL/Psycopg 3;
- SQLite как local/test fallback;
- Requests, Cryptography/Fernet, pypdf;
- Flask-WTF 1.3 и Flask-Limiter 4.1;
- HTML/CSS/JavaScript;
- GitHub Actions;
- vendor-neutral JSON logs, request IDs, health/readiness, optional alert webhook;
- encrypted PostgreSQL backup/restore;
- Render временно как staging/резерв, production VPS после INFRA/HOST.

## 3. Структура

```text
project/
├── app.py                         # Flask routes и WSGI app:app
├── config.py                      # environment/settings
├── database.py                    # engine, sessions, health, Alembic helpers
├── security.py                    # CSRF, rate limits, headers, request limits
├── observability.py               # logs, request IDs, metrics, alerts
├── operations/
│   └── backup.py                  # encrypted backup/verified restore
├── domain/
│   └── entities.py                # immutable detached records
├── models/
│   ├── base.py
│   ├── user.py
│   ├── oauth_connection.py
│   ├── vacancy.py                 # Vacancy + VacancySourceRecord
│   ├── sync_run.py
│   ├── sync_worker.py
│   └── accounts.py                # temporary legacy tables
├── repositories/
│   ├── users.py
│   ├── oauth_connections.py
│   ├── vacancies.py
│   ├── sync_runs.py
│   └── sync_workers.py
├── migrations/versions/
│   ├── 20260804_0001_initial_schema.py
│   ├── 20260804_0002_domain_model.py
│   └── 20260807_0003_external_sync_worker.py
├── services/
│   ├── storage.py                 # StorageServices bundle for app.py
│   ├── vacancy_store.py           # cache/query service API
│   ├── trudvsem_sync.py           # external sync orchestration
│   ├── sync_lock.py               # PostgreSQL/SQLite process lock
│   └── *_provider.py
├── scripts/
│   ├── backup_database.py
│   ├── verify_backup.py
│   ├── restore_database.py
│   ├── send_test_alert.py
│   ├── sync_trudvsem.py
│   ├── trudvsem_sync_worker.py
│   └── start_runtime.py
├── tests/
├── templates/
├── static/
├── render.yaml
└── .github/workflows/ci.yml
```

Главный файл — `app.py`; `app_fixed.py` не создаётся.

## 4. Границы слоёв

```text
Flask route
    -> application/service
        -> repository
            -> SQLAlchemy model/session
```

### app.py

- не импортирует SQLAlchemy, ORM models или concrete repositories;
- получает `StorageServices` как единую persistence boundary;
- использует совместимые aliases для OAuth, vacancy cache и SyncRun без SQL в routes.

### services

Нормализуют provider payload и реализуют application behavior. `VacancyStore` больше не содержит SQL statements.

### repositories

Единственное место application SQL queries. Возвращают immutable domain records либо JSON payload, а не session-bound ORM objects.

### models

Отражают persistence schema и relationships. Не содержат Flask/request logic.

## 5. Доменная схема DATA-002

```text
users
  id PK
  normalized_email UNIQUE nullable

users 1 ---- * oauth_connections
oauth_connections UNIQUE(provider, external_user_id)

vacancies 1 ---- * vacancy_source_records
vacancy_source_records UNIQUE(source, external_id)

sync_runs
```

### User

Identity skeleton для `AUTH-001`. Password/reset/verification entities не добавляются преждевременно.

### OAuthConnection

Unified provider connection. `user_id` nullable для compatibility с текущими session-based HH/SJ connections. `AUTH-002` привяжет rows к first-party user.

Legacy tables `accounts` и `hh_accounts` сохраняются временно как rollback mirror. Routes их не читают; `OAuthConnectionRepository` транзакционно зеркалирует известные HH/SuperJob writes до AUTH-002 cleanup.

### Vacancy и VacancySourceRecord

- `Vacancy` — canonical record;
- `VacancySourceRecord` — payload конкретного source.

На DATA-002 связь один-к-одному по фактическим данным. `SEARCH-002` сможет связать несколько source records с одной canonical vacancy, не меняя provider ingestion.

### SyncRun

Persistent lifecycle provider sync. После SYNC-001 status `queued` является durable job, а `running/succeeded/failed` отражают external worker execution. Partial unique index допускает только один active run на source.

## 6. Security boundary SEC-001

```text
request
  -> ProxyFix (trusted protocol only; client address is not rewritten)
  -> validated Cloudflare/Render client fingerprint for rate limits
  -> trusted host validation
  -> per-request size/form limits
  -> CSRFProtect / route-specific exemptions
  -> Flask-Limiter
  -> route/service/repository
  -> neutral error mapping
  -> security response headers + CSP nonce
```

`security.py` не содержит business logic и может повторно использоваться будущими blueprints. `config.py` является единственным источником policy values. Production принудительно требует secure cookie, CSRF, rate limiting и security headers. При `TRUST_PROXY_HEADERS=1` limiter использует валидный `CF-Connecting-IP` или первый IP `X-Forwarded-For`, сохраняет только HMAC fingerprint и игнорирует forwarded headers в остальных режимах.

### Browser session

- host-only `aca_session`;
- `Secure`, `HttpOnly`, production-enforced `SameSite=Lax`;
- 12-hour permanent lifetime по умолчанию;
- session очищается после успешного OAuth, provider identities сохраняются;
- OAuth state одноразовый, имеет TTL 10 минут и проверяется до обработки success/error/cancel callback; production OAuth redirect URI обязаны использовать HTTPS.

### Public и diagnostic surfaces

- public UI получает только `/api/sources/trudvsem/status`;
- `/debug/*` и detailed `/trudvsem/status` требуют explicit diagnostics mode + header secret;
- `/sync/trudvsem` использует `X-Sync-Secret` и CSRF exemption только как machine endpoint;
- `/trudvsem/refresh` недоступен в production;
- logout — POST + CSRF.

### Headers и front-end contract

CSP использует request nonce, запрещает inline event handlers и не разрешает произвольные внешние images. Все `<script>` templates обязаны иметь `nonce="{{ csp_nonce }}"`; inline event handlers запрещены и контролируются static tests. Existing inline styles временно разрешены до PERF/A11Y cleanup.

### Resource and outbound controls

Upload/body/form/PDF limits применяются до дорогостоящей обработки. University-logo resolver валидирует DNS/IP, каждый redirect, MIME/signature и response size, что формирует SSRF baseline.

### Ограничение масштабирования

`RATELIMIT_STORAGE_URI=memory://` подходит текущему одному worker. При масштабировании storage должен стать общим, например Redis-compatible; это operational dependency OPS/INFRA.

## 7. Operational boundary OPS-001

```text
HTTP request
  -> request ID + timer
  -> SEC-001 controls
  -> route/service/repository
  -> X-Request-ID + bounded access metric/log

provider call
  -> provider_operation(name, operation)
  -> success/failure/timeout/latency metric

ERROR log
  -> sanitizer
  -> bounded recent-errors registry
  -> optional HTTPS alert queue
```

`observability.py` запрещает запись request body, query string, cookies, OAuth tokens, database credentials и resume text. Production writes one JSON object per stdout line. Metrics/recent errors process-local и доступны только через diagnostics-authenticated `/ops/status`.

Health contract:

- `/health/live` - process liveness, без базы;
- `/health/ready` - DB connectivity + expected Alembic revision;
- `/health` - compatibility alias readiness.

Backup contract:

- PostgreSQL: `pg_dump` custom format + `pg_restore --list`;
- optional mandatory production AES-256-GCM encryption;
- manifest + SHA-256 + revision + controlled row counts;
- restore в отдельную DB и post-restore inventory verification;
- production restore требует explicit override.

OPS-001 сам schema не менял. SYNC-001 добавляет revision `20260807_0003`; production restore drill остаётся release gate OPS-002/REL-001.

## 8. Миграции

### 20260804_0001

Создаёт legacy pre-MVP schema и принимает старый SQLite.

### 20260804_0002

- создаёт `users`, `oauth_connections`, `sync_runs`;
- копирует legacy HH/SJ rows без изменения encrypted tokens;
- преобразует старую source-only `vacancies` в canonical/source model;
- сохраняет source IDs, raw JSON, search fields и timestamps;
- поддерживает SQLite/PostgreSQL;
- имеет downgrade для staging/backup rehearsal и выравнивает PostgreSQL serial sequences после копирования explicit IDs.

### 20260807_0003

- закрывает legacy abandoned `running` sync rows как failed;
- добавляет partial unique index `uq_sync_runs_active_source`;
- создаёт `sync_workers` для external process heartbeat;
- не меняет vacancy/OAuth/user payload;
- поддерживает SQLite/PostgreSQL и controlled downgrade.

Alembic — единственный production schema mechanism. `Base.metadata.create_all()` разрешён только в изолированных tests.

## 9. Runtime database

`DatabaseRuntime` предоставляет Engine/sessionmaker и secret-free health. Production подтверждён на PostgreSQL 17.

После DATA-002 deploy ожидается:

```text
backend=postgresql
persistent=true
configured=true
revision=20260807_0003
```

## 10. OAuth compatibility

Current browser session по-прежнему хранит внешний provider user ID. StorageServices передаёт запрос repository, unified connection преобразуется в прежний mapping для existing routes/templates. Token encryption/refresh behavior не меняются; обновления временно dual-write в legacy tables.

## 11. Vacancy compatibility

Provider ingestion и template payload не меняются. `VacancyStore`:

1. нормализует provider dict;
2. передаёт source payload repository;
3. создаёт/обновляет canonical + source record;
4. возвращает прежний raw JSON format для search UI.

## 12. Sync state

SYNC-001 удаляет process-local queue/event/thread из Flask. Координация хранится в PostgreSQL:

```text
sync_runs      durable queue and execution lifecycle
sync_workers   process heartbeat/liveness
```

Web routes создают idempotent `queued` run. External worker выполняет provider HTTP под PostgreSQL advisory lock (SQLite fallback — stale-aware lockfile), обновляет progress и переводит run в terminal state. Public status sanitised; diagnostic status может показать persisted run и worker heartbeat.

## 13. Собственный домен

`DOMAIN-001` не потерян. В плане 1.3.x он выполняется после `HOST-001` и до `MIG-001`, чтобы постоянный URL не зависел от конкретного VPS.

Зависимости домена:

- secure cookies/CSRF/trusted hosts (`SEC-001`);
- monitoring/backup/rollback (`OPS-001`);
- проверенный VPS (`INFRA-001`, `HOST-001`);
- `PUBLIC_BASE_URL`, OAuth callback changes, DNS/TLS (`DOMAIN-001`);
- data/DNS switch (`MIG-001`).

## 14. Deploy и rollback

Текущий Render start command для SYNC-001 candidate:

```bash
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Supervisor запускает Gunicorn и Trudvsem worker как sibling OS processes. На VPS Compose web остаётся отдельным от `sync-worker`.

Rollback DATA-002:

- не удалять PostgreSQL;
- не делать downgrade единственной production DB без backup;
- предпочтительно восстановить backup/clone и переключить `DATABASE_URL`;
- rollback application на schema 0001 допустим только после controlled data rollback.

## 15. Следующие границы

- завершить GitHub/Render verification `SYNC-001`;
- `SYNC-002`: freshness watermark, retries и cleanup policy;
- `SEARCH-001/002/003/004`: normalization, dedup и stable pagination;
- `AUTH/PROFILE`, AI functions и JOB tracker;
- перед beta: `INFRA-001` -> `REED-COMPAT-001` -> `HOST-001` -> `OPS-002` -> `DOMAIN-001` -> `MIG-001`.
## 16. INFRA-001 container boundary

```text
Caddy (optional TLS profile)
    -> non-root Gunicorn/Flask runtime
        -> internal PostgreSQL 17 network

one-shot migrate service
OPS image with PostgreSQL 17 tools
isolated restore-test PostgreSQL profile
```

- Production Render не изменяется этим пакетом.
- PostgreSQL services не публикуют host ports.
- Web публикуется напрямую только во время controlled IPv4 test; с Caddy он привязан к localhost.
- Один Gunicorn worker сохраняется до shared limiter storage; Trudvsem provider I/O уже вынесен в external worker.
- OPS target используется для encrypted backup/restore, а не для web traffic.
- Реальная доступность из РФ/РБ фиксируется `scripts/infra_probe.py` и матрицей `docs/INFRA001_VPS_TEST.md`.

## 17. SYNC-001 process boundary

```text
Render staging container
  scripts/start_runtime.py
    ├── Gunicorn -> Flask routes -> PostgreSQL cache / durable enqueue
    └── sync worker -> advisory lock -> Trudvsem API -> PostgreSQL upsert

VPS / Docker Compose
  web service         (Gunicorn only)
  sync-worker service (provider I/O only)
  db service          (private network)
```

Ключевая гарантия: web request не запускает network sync и не ждёт provider API. Failure external worker не удаляет cache и не останавливает web.


# AI Career Agent — архитектура проекта

> Последнее обновление: 05 августа 2026 года  
> Текущий пакет: `SEC-001` — базовое усиление безопасности  
> Статус пакета: **НУЖНА ПРОВЕРКА**

## 1. Цель архитектуры

```text
аккаунт -> карьерный профиль -> анализ резюме -> поиск вакансий
-> объяснимое совпадение -> письмо -> трекер откликов
```

Инфраструктура не должна быть жёстко привязана к Render. До первой commercial beta рекомендуемая production-схема — платный Render + собственный домен + managed PostgreSQL. Тот же application code должен переноситься на VPS без изменения бизнес-логики.

## 2. Технологический стек

- Python 3.11, Flask 3.1.3, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL/Psycopg 3;
- SQLite как local/test fallback;
- Requests, Cryptography/Fernet, pypdf;
- Flask-WTF 1.3 и Flask-Limiter 4.1;
- HTML/CSS/JavaScript;
- GitHub Actions;
- Render сейчас, собственный домен до beta, optional VPS позже.

## 3. Структура

```text
project/
├── app.py                         # Flask routes и WSGI app:app
├── config.py                      # environment/settings
├── database.py                    # engine, sessions, health, Alembic helpers
├── security.py                    # CSRF, rate limits, headers, request limits
├── domain/
│   └── entities.py                # immutable detached records
├── models/
│   ├── base.py
│   ├── user.py
│   ├── oauth_connection.py
│   ├── vacancy.py                 # Vacancy + VacancySourceRecord
│   ├── sync_run.py
│   └── accounts.py                # temporary legacy tables
├── repositories/
│   ├── users.py
│   ├── oauth_connections.py
│   ├── vacancies.py
│   └── sync_runs.py
├── migrations/versions/
│   ├── 20260804_0001_initial_schema.py
│   └── 20260804_0002_domain_model.py
├── services/
│   ├── storage.py                 # StorageServices bundle for app.py
│   ├── vacancy_store.py           # payload normalization/service API
│   └── *_provider.py
├── scripts/
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

Persistent lifecycle provider sync. Trudvsem сохраняет start/finish, processed/saved/cursor/error. Scheduler/thread architecture остаётся до `SYNC-001`.

## 6. Security boundary SEC-001

```text
request
  -> ProxyFix (one trusted platform proxy)
  -> trusted host validation
  -> per-request size/form limits
  -> CSRFProtect / route-specific exemptions
  -> Flask-Limiter
  -> route/service/repository
  -> neutral error mapping
  -> security response headers + CSP nonce
```

`security.py` не содержит business logic и может повторно использоваться будущими blueprints. `config.py` является единственным источником policy values. Production принудительно требует secure cookie, CSRF, rate limiting и security headers.

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

## 7. Миграции

### 20260804_0001

Создаёт legacy pre-MVP schema и принимает старый SQLite.

### 20260804_0002

- создаёт `users`, `oauth_connections`, `sync_runs`;
- копирует legacy HH/SJ rows без изменения encrypted tokens;
- преобразует старую source-only `vacancies` в canonical/source model;
- сохраняет source IDs, raw JSON, search fields и timestamps;
- поддерживает SQLite/PostgreSQL;
- имеет downgrade для staging/backup rehearsal и выравнивает PostgreSQL serial sequences после копирования explicit IDs.

Alembic — единственный production schema mechanism. `Base.metadata.create_all()` разрешён только в изолированных tests.

## 8. Runtime database

`DatabaseRuntime` предоставляет Engine/sessionmaker и secret-free health. Production подтверждён на PostgreSQL 17.

После DATA-002 deploy ожидается:

```text
backend=postgresql
persistent=true
configured=true
revision=20260804_0002
```

## 9. OAuth compatibility

Current browser session по-прежнему хранит внешний provider user ID. StorageServices передаёт запрос repository, unified connection преобразуется в прежний mapping для existing routes/templates. Token encryption/refresh behavior не меняются; обновления временно dual-write в legacy tables.

## 10. Vacancy compatibility

Provider ingestion и template payload не меняются. `VacancyStore`:

1. нормализует provider dict;
2. передаёт source payload repository;
3. создаёт/обновляет canonical + source record;
4. возвращает прежний raw JSON format для search UI.

## 11. Sync state

In-memory state пока остаётся для текущего UI/worker. Дополнительно каждый run сохраняется в `sync_runs`, а `/trudvsem/status` может показать `persisted_run`. Полный вынос worker из Gunicorn выполняется в `SYNC-001`.

## 12. Собственный домен

`DOMAIN-001` не потерян и не интегрирован в DATA-002. Он находится в этапе 6 и в ближайшей последовательности после `SEC-001` и `OPS-001`.

Зависимости домена:

- secure cookies/CSRF/trusted hosts (`SEC-001`);
- monitoring/rollback (`OPS-001`);
- `PUBLIC_BASE_URL`, OAuth callback changes, DNS/TLS (`DOMAIN-001`).

## 13. Deploy и rollback

Текущий Render start command:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

Rollback DATA-002:

- не удалять PostgreSQL;
- не делать downgrade единственной production DB без backup;
- предпочтительно восстановить backup/clone и переключить `DATABASE_URL`;
- rollback application на schema 0001 допустим только после controlled data rollback.

## 14. Следующие границы

- `SEC-001`: security middleware/forms/session flags;
- `OPS-001`: structured logs, backup restore, alerts;
- `DOMAIN-001`: domain/DNS/TLS/public URLs;
- `SYNC-001`: отдельный worker command;
- `AUTH-001/002`: first-party user и binding OAuth connections.

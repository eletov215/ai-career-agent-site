# AI Career Agent

Flask-приложение с OAuth-интеграциями HeadHunter и SuperJob, единым поиском вакансий, кэшем «Работы России», загрузкой PDF-резюме и конструктором резюме.

## Текущий статус

- `FND-001` — **ВЫПОЛНЕНО**: базовые тесты и GitHub Actions подтверждены.
- `FND-002` — **ВЫПОЛНЕНО**: конфигурация `development/test/production` подтверждена CI и Render; `HH_CURRENCY_SCAN_PAGES=20`.
- `DATA-001` — **ВЫПОЛНЕНО**: production PostgreSQL 17, Alembic revision `20260804_0001` и сохранность после restart подтверждены.
- `DATA-002` — **ВЫПОЛНЕНО**: domain/repository layers и migration `20260804_0002` подтверждены зелёным CI, Render и restart persistence.
- `SEC-001` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА НА RENDER**: CSRF/headers/cookie/PDF/search/log smoke подтверждены; исправлен нестабильный rate-limit key за Cloudflare/Render, требуется повторный CI и production `429` probe.
- `OPS-001` — **НУЖНА ПРОВЕРКА**: observability, live/readiness, alerts и encrypted backup/restore реализованы; требуются зелёный CI, тест доставки alert и production restore drill.

Главный рабочий файл остаётся `app.py`. WSGI-приложение — `app:app`; `app_fixed.py` не используется.

## Конфигурация

Настройки централизованы в `config.py`. Режим задаётся через `APP_ENV`:

| Режим | Назначение |
|---|---|
| `production` | Публичный сервис. Используется по умолчанию. |
| `development` | Локальная разработка; секреты задаются явно. |
| `test` | Автоматические тесты с безопасными фиктивными OAuth-настройками. |

### Обязательные переменные production/development

```text
FLASK_SECRET_KEY
TOKEN_ENCRYPTION_KEY
SUPERJOB_CLIENT_ID
SUPERJOB_CLIENT_SECRET
SUPERJOB_REDIRECT_URI
HH_CLIENT_ID
HH_CLIENT_SECRET
HH_REDIRECT_URI
HH_USER_AGENT
```

### База данных

```text
DATABASE_URL
```

Поддерживаются PostgreSQL/Psycopg 3 и SQLite local/test fallback. `postgres://` и `postgresql://` автоматически нормализуются в `postgresql+psycopg://`.

Без `DATABASE_URL` приложение использует:

```text
sqlite:///<DATA_DIR>/app.db
```

Это допустимо локально и в тестах, но production уже подтверждён на PostgreSQL.

### Другие необязательные переменные

```text
HH_APP_TOKEN
REED_API_KEY
SYNC_SECRET
DATA_DIR
VACANCY_CACHE_TTL
VACANCY_PAGE_SIZE
TRUDVSEM_SYNC_ENABLED
TRUDVSEM_SYNC_INTERVAL
TRUDVSEM_SYNC_ITEMS
TRUDVSEM_SYNC_BATCH
TRUDVSEM_REQUEST_ATTEMPTS
TRUDVSEM_RETRY_BACKOFF
HH_CURRENCY_SCAN_PAGES
DEBUG_HH
MAX_RESUME_UPLOAD_MB
MAX_RESUME_PAGES
MAX_RESUME_TEXT_CHARACTERS
SESSION_COOKIE_SECURE
SESSION_COOKIE_SAMESITE
SESSION_LIFETIME_SECONDS
CSRF_ENABLED
CSRF_TIME_LIMIT_SECONDS
RATE_LIMIT_ENABLED
RATELIMIT_STORAGE_URI
TRUSTED_HOSTS
TRUST_PROXY_HEADERS
SECURITY_HEADERS_ENABLED
HSTS_SECONDS
MAX_FORM_MEMORY_SIZE
MAX_FORM_PARTS
DEBUG_DIAGNOSTICS
DIAGNOSTICS_SECRET
SERVICE_NAME
APP_VERSION
LOG_LEVEL
LOG_FORMAT
OPS_ALERT_WEBHOOK_URL
OPS_ALERT_WEBHOOK_TOKEN
OPS_ALERT_TIMEOUT_SECONDS
OPS_ALERT_MIN_LEVEL
BACKUP_DIR
BACKUP_RETENTION_DAYS
BACKUP_ENCRYPTION_KEY
FLASK_DEBUG
PORT
```

`HH_CURRENCY_SCAN_PAGES` допускает `1..20`; Render использует `20`.

## Базовый защитный слой SEC-001

Добавлены Flask-WTF и Flask-Limiter, а политика собрана в `security.py`. Production по умолчанию использует:

- host-only cookie `aca_session` с `Secure`, `HttpOnly`, обязательным production `SameSite=Lax` и ограниченным сроком жизни;
- глобальную CSRF-проверку для POST/PUT/PATCH/DELETE;
- route-specific rate limits для OAuth, загрузок, поиска, diagnostics и sync;
- CSP с nonce для скриптов, HSTS, clickjacking/MIME/referrer/permissions/cross-origin headers;
- лимиты размера запроса, числа multipart-полей, страниц PDF и извлечённого текста;
- нейтральные 400/404/405/413/429/500 ответы без отражения provider details; OAuth state проверяется также при cancel/error callback;
- закрытые `/debug/*` и `/trudvsem/status`; production refresh endpoint возвращает 404; `/sync/trudvsem` остаётся доступен только по `X-Sync-Secret`;
- public status для интерфейса: `/api/sources/trudvsem/status`, без ошибок и внутренних полей;
- проверку внешних URL/redirects/изображений в university-logo resolver для снижения SSRF и oversized-response рисков.

Новых обязательных переменных для обычного production deploy нет. Production OAuth callback URL должны использовать HTTPS; credentials и URL fragments запрещены. Детальная диагностика выключена по умолчанию. Для временного включения нужны одновременно:

```text
DEBUG_DIAGNOSTICS=1
DIAGNOSTICS_SECRET=<случайное длинное значение>
```

и заголовок `X-Diagnostics-Secret`. Не передавайте секрет в URL. Rate-limit client key за Render/Cloudflare строится из валидированного forwarded client IP и сохраняется как HMAC fingerprint. Для production smoke существует безопасный `GET /api/security/rate-limit-probe`: первые 5 запросов в минуту возвращают 200, следующий должен вернуть 429 и `Retry-After`. `RATELIMIT_STORAGE_URI=memory://` подходит текущему одному Gunicorn worker; при горизонтальном масштабировании потребуется общее Redis-compatible storage. Подробности: [`docs/SECURITY.md`](docs/SECURITY.md).

## Наблюдаемость и восстановление OPS-001

OPS-001 добавляет vendor-neutral operational foundation:

- JSON-логи в stdout в production и читаемый text-формат локально;
- `X-Request-ID` для корреляции HTTP-запросов;
- bounded HTTP/provider metrics и последние sanitised ошибки;
- optional HTTPS alert webhook без request body, query string, cookies, токенов и текста резюме;
- отдельные endpoints `/health/live` и `/health/ready`; `/health` остаётся совместимым alias readiness;
- encrypted PostgreSQL/SQLite backups с manifest, SHA-256 и проверяемым restore;
- diagnostics-only `/ops/status` и `/ops/alerts/test`.

Обычный deploy не требует новых обязательных переменных. Для alert webhook используются:

```text
OPS_ALERT_WEBHOOK_URL=https://...
OPS_ALERT_WEBHOOK_TOKEN=<optional bearer token>
OPS_ALERT_TIMEOUT_SECONDS=3
OPS_ALERT_MIN_LEVEL=ERROR
```

Для production backup обязателен отдельный ключ:

```bash
python - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
```

Полученное значение хранится как `BACKUP_ENCRYPTION_KEY`, отдельно от `TOKEN_ENCRYPTION_KEY`. Основные команды:

```bash
python scripts/backup_database.py --output-dir backups
python scripts/verify_backup.py --backup backups/<file>.enc
RESTORE_DATABASE_URL='postgresql+psycopg://...' \
  python scripts/restore_database.py --backup backups/<file>.enc
```

Не храните backups и manifests в Git. Подробности: [`docs/OPERATIONS.md`](docs/OPERATIONS.md), [`docs/BACKUP_RESTORE.md`](docs/BACKUP_RESTORE.md), [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md).

## Данные и доменная модель

### DATA-001

Добавлены SQLAlchemy 2, Alembic, Psycopg 3, `DATABASE_URL`, первая migration `20260804_0001`, `/health` и legacy SQLite importer.

### DATA-002

Candidate schema revision `20260804_0002` добавляет:

```text
users
oauth_connections
vacancies                 # canonical vacancy
vacancy_source_records    # provider-specific payload
sync_runs
```

Legacy `accounts` и `hh_accounts` временно сохраняются для rollback. Чтение выполняется из `oauth_connections`, а записи HH/SuperJob в период verification транзакционно зеркалируются и в legacy-таблицы.

Слой доступа:

```text
domain/             # detached immutable records
repositories/       # SQLAlchemy queries
services/storage.py # единая точка persistence для app.py
services/           # normalization/application behavior
app.py              # routes, без SQLAlchemy/ORM/repository imports
```

`VacancyStore` сохраняет прежний публичный API, но делегирует SQL в `VacancyRepository`. Подробности: [`docs/DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md).

## Миграции

Основные команды:

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
```

Локальный запуск:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/manage_db.py upgrade
python app.py
```

Текущий Render start command:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

После deploy DATA-002 `/health` должен сообщать:

```json
{
  "status": "ok",
  "database": {
    "ok": true,
    "backend": "postgresql",
    "persistent": true,
    "revision": "20260804_0002",
    "configured": true
  }
}
```

## Перенос legacy SQLite

```bash
DATABASE_URL='postgresql+psycopg://...' \
python scripts/import_legacy_sqlite.py --source /path/to/app.db
```

Importer пишет provider identities в `oauth_connections` и вакансии через новый canonical/source repository. Нужен прежний `TOKEN_ENCRYPTION_KEY`.

Подробный порядок: [`docs/DATABASE_MIGRATION.md`](docs/DATABASE_MIGRATION.md).

## Тесты и CI

Перед push:

```bash
python scripts/check_repository_hygiene.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories operations migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest -ra
```

GitHub Actions поднимает PostgreSQL 17, проверяет migration из legacy revision `0001` в `0002`, serial sequence после backfill, `alembic check`, repository/domain boundaries, SEC-001 controls, OPS-001 observability tests и реальный encrypted PostgreSQL backup/restore в отдельную тестовую базу.

## Зафиксированная инфраструктурная очередь

Render временно остаётся staging/резервной площадкой. Production-путь согласно PLAN_CURRENT 1.3.x:

```text
SEC-001 rate-limit recheck
-> OPS-001 verification
-> INFRA-001 test VPS
-> AI-BENCH-001
-> REED-COMPAT-001
-> AI-PROVIDER-001
-> HOST-001
-> DOMAIN-001
-> MIG-001
```

`DOMAIN-001` не потерян: он выполняется после подготовки VPS и до миграции production, чтобы пользовательский адрес не зависел от конкретного сервера.

## Текущие ограничения

- SEC-001 прошёл CI, но ожидает production security smoke на Render из доступной сети.
- OPS-001 ожидает GitHub/production verification, реальную доставку alert и restore drill; до этого пакет нельзя считать выполненным.
- Rate limiting пока использует process-local memory storage; для нескольких workers/instances нужен общий backend.
- Trudvsem worker пока работает внутри web-процесса (`SYNC-001`).
- Собственный пользователь и account UI ещё не реализованы (`AUTH-001`).
- `user_id` в `oauth_connections` пока nullable и будет заполняться в `AUTH-002`.
- Canonical vacancy пока создаётся один-к-одному с source record; cross-source merge появится в `SEARCH-002`.
- Реального LLM-провайдера пока нет; Yandex AI Studio/Alice AI будет оцениваться в AI-BENCH-001.
- Operational metrics и alert queue пока process-local; перед несколькими workers/instances потребуется shared backend/exporter.
- Offsite backup storage и расписание backup ещё должны быть настроены на выбранной production-площадке.
- Общая дедупликация и стабильная единая пагинация остаются будущими пакетами.

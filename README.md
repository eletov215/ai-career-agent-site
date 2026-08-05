# AI Career Agent

Flask-приложение с OAuth-интеграциями HeadHunter и SuperJob, единым поиском вакансий, кэшем «Работы России», загрузкой PDF-резюме и конструктором резюме.

## Текущий статус

- `FND-001` — **ВЫПОЛНЕНО**: базовые тесты и GitHub Actions подтверждены.
- `FND-002` — **ВЫПОЛНЕНО**: конфигурация `development/test/production` подтверждена CI и Render; `HH_CURRENCY_SCAN_PAGES=20`.
- `DATA-001` — **ВЫПОЛНЕНО**: production PostgreSQL 17, Alembic revision `20260804_0001` и сохранность после restart подтверждены.
- `DATA-002` — **НУЖНА ПРОВЕРКА**: доменная schema/repositories и migration `20260804_0002` подготовлены; нужен зелёный CI и Render verification.

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
FLASK_DEBUG
PORT
```

`HH_CURRENCY_SCAN_PAGES` допускает `1..20`; Render использует `20`.

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
python -m compileall -q app.py config.py database.py domain models repositories migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest -ra
```

GitHub Actions поднимает PostgreSQL 17, проверяет migration из legacy revision `0001` в `0002`, serial sequence после backfill, `alembic check`, repository/domain boundaries и persistence после пересоздания Engine.

## Собственный домен

Пакет не потерян и не объединён с DATA-002:

```text
DOMAIN-001 — собственный домен, DNS, TLS и публичные URL
```

Он находится в этапе 6 и выполняется после `SEC-001` и `OPS-001`, до публичной beta. Домен сначала может указывать на Render; последующий переход на VPS меняет DNS target, но не пользовательский адрес.

## Текущие ограничения

- Trudvsem worker пока работает внутри web-процесса (`SYNC-001`).
- Собственный пользователь и account UI ещё не реализованы (`AUTH-001`).
- `user_id` в `oauth_connections` пока nullable и будет заполняться в `AUTH-002`.
- Canonical vacancy пока создаётся один-к-одному с source record; cross-source merge появится в `SEARCH-002`.
- Реального LLM-провайдера пока нет.
- Общая дедупликация и стабильная единая пагинация остаются будущими пакетами.

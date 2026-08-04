# AI Career Agent

Flask-приложение с OAuth-интеграциями HeadHunter и SuperJob, единым поиском вакансий, кэшем «Работы России», загрузкой PDF-резюме и конструктором резюме.

## Текущий статус

- `FND-001` — **ВЫПОЛНЕНО**: базовые тесты и GitHub Actions подтверждены.
- `FND-002` — **ВЫПОЛНЕНО**: конфигурация `development/test/production` подтверждена CI и Render; `HH_CURRENCY_SCAN_PAGES=20`.
- `DATA-001` — **НУЖНА ПРОВЕРКА**: SQLAlchemy, Alembic и PostgreSQL-поддержка добавлены; требуется создать PostgreSQL, выполнить deploy и подтвердить постоянное хранение.

Главный рабочий файл остаётся `app.py`. WSGI-приложение остаётся `app:app`; файлы наподобие `app_fixed.py` не используются.

## Конфигурация

Настройки централизованы в `config.py`. Режим задаётся через `APP_ENV`:

| Режим | Назначение |
|---|---|
| `production` | Публичный сервис. Используется по умолчанию для обратной совместимости. |
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

### Переменная базы данных

```text
DATABASE_URL
```

Поддерживаются:

```text
postgresql+psycopg://user:password@host:5432/database
postgresql://user:password@host:5432/database
postgres://user:password@host:5432/database
sqlite:////absolute/path/app.db
```

`postgres://` и `postgresql://` автоматически приводятся к драйверу Psycopg 3.

Если `DATABASE_URL` не задан, приложение временно сохраняет обратную совместимость и использует:

```text
sqlite:///<DATA_DIR>/app.db
```

Этот fallback удобен для локальной разработки, но **не является постоянным production-хранилищем на Render**. Для завершения `DATA-001` production должен использовать PostgreSQL.

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

`HH_CURRENCY_SCAN_PAGES` допускает значения от `1` до `20`. Для текущего Render-сервиса используется `20`.

## База данных и миграции

`DATA-001` добавляет:

- SQLAlchemy 2;
- Alembic;
- Psycopg 3;
- модели текущих таблиц `accounts`, `hh_accounts`, `vacancies`;
- первую миграцию `20260804_0001`;
- секрет-безопасный статус базы в `/health`;
- необязательный импорт снимка старой SQLite-базы.

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

Production start command на текущем бесплатном Render:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

После перехода на платный Render или VPS миграцию следует вынести в отдельную pre-deploy/entrypoint-фазу.

## Перенос старой SQLite-базы

Кэш вакансий можно восстановить повторной синхронизацией. Для переноса существующих OAuth-подключений нужен реальный снимок старого `app.db` и тот же `TOKEN_ENCRYPTION_KEY`.

```bash
DATABASE_URL='postgresql+psycopg://...' \
python scripts/import_legacy_sqlite.py --source /path/to/app.db
```

Скрипт выполняет upsert текущих таблиц. Перед переносом production-данных необходимо сделать резервную копию и сначала проверить импорт на тестовой базе.

Подробный порядок: [`docs/DATABASE_MIGRATION.md`](docs/DATABASE_MIGRATION.md).

## Render: завершение DATA-001

1. Создать PostgreSQL в том же регионе, что и web service.
2. В `Environment` web service добавить `DATABASE_URL` из **Internal Database URL**.
3. Сохранить прежний `TOKEN_ENCRYPTION_KEY`.
4. Выполнить deploy текущего commit.
5. Убедиться, что start command завершил миграцию.
6. Открыть `/health` и проверить:

```json
{
  "status": "ok",
  "database": {
    "ok": true,
    "backend": "postgresql",
    "persistent": true,
    "revision": "20260804_0001",
    "configured": true
  }
}
```

7. Проверить OAuth, поиск вакансий, `/resume-builder` и перезапуск/redeploy.

## Тесты и CI

Перед push:

```bash
python scripts/check_repository_hygiene.py
python -m compileall -q app.py config.py database.py models migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest
```

GitHub Actions устанавливает production- и test-зависимости, применяет миграции к изолированной SQLite-базе и к отдельному PostgreSQL 17 service container, проверяет отсутствие новых незаписанных миграций и выполняет реальный PostgreSQL round-trip для OAuth-аккаунтов и вакансии. Внешние API в CI заменены mock-ответами.

## Текущие ограничения

- Фоновая синхронизация Trudvsem пока работает внутри web-процесса; перенос запланирован в `SYNC-001`.
- Собственный пользователь AI Career Agent ещё не реализован.
- Реального LLM-провайдера пока нет.
- Общая межисточниковая дедупликация и стабильная единая пагинация ещё требуют отдельных пакетов.
- Собственный домен обязателен к коммерческому запуску; код должен оставаться переносимым между Render и VPS.

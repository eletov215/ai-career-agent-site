# DATA-002 — базовая доменная модель и repository layer

## Цель

Отделить Flask routes и application services от SQLAlchemy-запросов и подготовить стабильную схему для будущих пакетов `AUTH`, `PROFILE`, `SEARCH`, `SYNC` и `JOB`.

## Новые сущности

```text
User 1 ─── * OAuthConnection

Vacancy 1 ─── * VacancySourceRecord

SyncRun
```

### User

Первичная identity AI Career Agent. В DATA-002 таблица содержит только нейтральные поля identity и статуса. Password hash, verification/reset tokens и UI намеренно остаются в `AUTH-001`.

### OAuthConnection

Единая таблица для внешних OAuth-идентичностей. Текущие SuperJob и HeadHunter rows мигрируются из `accounts` и `hh_accounts`. `user_id` пока nullable: существующие подключения продолжают работать без собственного аккаунта и позже могут быть привязаны в `AUTH-002`.

Legacy-таблицы `accounts` и `hh_accounts` пока не удаляются. Приложение читает unified `oauth_connections`; HH/SuperJob writes транзакционно зеркалируются в legacy tables до AUTH-002, чтобы немедленный application rollback не получил устаревшие tokens.

### Vacancy

Каноническая вакансия. На первом шаге каждой source record соответствует отдельная canonical vacancy. Это сохраняет текущую выдачу без изменения поведения и подготавливает модель для `SEARCH-002`, где несколько source records смогут быть привязаны к одной вакансии.

### VacancySourceRecord

Оригинальная запись конкретного источника: `source + external_id`, raw JSON, URL, индексы фильтрации и timestamps. Старая таблица `vacancies` преобразуется в `vacancy_source_records`; данные копируются без потери, а IDs source rows сохраняются.

### SyncRun

Постоянная запись запуска синхронизации: источник, trigger, status, processed/saved, cursor и нейтральная ошибка. Текущий Trudvsem worker сохраняет start/finish в эту таблицу, но сам daemon thread остаётся внутри web process до `SYNC-001`.

## Repository layer

```text
repositories/
├── users.py
├── oauth_connections.py
├── vacancies.py
└── sync_runs.py
```

- `app.py` импортирует только `StorageServices`, а не SQLAlchemy/ORM/concrete repositories.
- `StorageServices` собирает User/OAuth/SyncRun repositories и VacancyStore.
- OAuth helpers работают через unified repository с временным legacy dual-write.
- `VacancyStore` нормализует provider payload, но SQL-запросы выполняет `VacancyRepository`.
- Sync worker пишет lifecycle через `SyncRunRepository`.
- Repositories возвращают immutable User/OAuth/Vacancy/Source/SyncRun records, а не session-bound ORM objects.

## Migration 20260804_0002

Migration выполняет:

1. создание `users`, `oauth_connections`, `sync_runs`;
2. копирование legacy OAuth rows без расшифровки/изменения tokens;
3. временное переименование старой `vacancies`;
4. создание canonical `vacancies` и `vacancy_source_records`;
5. backfill canonical row для каждой source vacancy;
6. сохранение source row IDs, raw JSON и search fields;
7. выравнивание PostgreSQL sequence после копирования explicit source IDs;
8. удаление только временной vacancy table после успешного копирования.

Migration поддерживает SQLite и PostgreSQL. Downgrade восстанавливает прежнюю таблицу `vacancies`, но в production downgrade без backup запрещён.

## Совместимость

- Текущие OAuth sessions продолжают использовать provider external ID.
- Текущие templates получают прежние dict keys (`name`, `first_name`, `access_token` и т. д.).
- Публичный API `VacancyStore` не меняется.
- UI, маршруты поиска и формат карточек не меняются.
- Existing PostgreSQL rows переходят на revision `20260804_0002` при deploy.

## Проверки

- migration чистой SQLite;
- adoption legacy SQLite;
- OAuth copy из legacy tables;
- migration downgrade/upgrade round-trip;
- `alembic check`;
- User/OAuth/SyncRun repositories;
- canonical/source vacancy relationship и cascade;
- architectural boundary test: routes не знают SQLAlchemy;
- PostgreSQL 17 integration test мигрирует seeded legacy rows, проверяет OAuth copy/dual-write, sequence continuity и reconnect persistence.

## Production verification

После merge/deploy:

1. `python scripts/manage_db.py upgrade` должен применить `20260804_0002`;
2. `/health` должен показать `revision=20260804_0002`;
3. `/`, `/vacancies/internal`, OAuth dashboard и `/trudvsem/status` должны работать;
4. legacy OAuth connection, если он существует, должен остаться доступным;
5. `cached_total` до и после restart должен сохраниться;
6. `/trudvsem/status` после нового sync должен содержать `persisted_run`.

## Rollback

- Не удалять PostgreSQL.
- Откат application commit допустим только с пониманием, что старый код ожидает schema `0001`.
- Предпочтительный rollback — restore backup/new database + переключение `DATABASE_URL`.
- `alembic downgrade 20260804_0001` выполнять только на backup/staging, не на единственной production database.

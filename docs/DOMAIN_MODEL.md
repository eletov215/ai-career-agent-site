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

Каноническая вакансия. После SEARCH-002 несколько безопасно совпавших публикаций разных providers могут ссылаться на одну canonical vacancy. Existing `fingerprint` сохраняет source-identity роль; SEARCH-002 хранит versioned candidate key отдельно в nullable `dedup_key`/`dedup_version`. Same-provider разные external IDs остаются разными canonical vacancies.

### VacancySourceRecord

Оригинальная запись конкретного источника: `source + external_id`, raw JSON, URL, canonical filter fields и timestamps. SEARCH-002 не удаляет source rows: объединение означает только общую ссылку `vacancy_id` на canonical Vacancy.

### SyncRun

Постоянная запись запуска синхронизации: источник, trigger, status, processed/saved, cursor и нейтральная ошибка. С SYNC-001 Trudvsem lifecycle хранится в этой таблице как durable queue: web-процесс только создаёт `queued` run, а отдельный worker переводит его в `running` и terminal status. Частичный unique index допускает не более одного активного run для источника.

## Repository layer

```text
repositories/
├── users.py
├── oauth_connections.py
├── vacancies.py
├── sync_runs.py
└── sync_workers.py
```

- `app.py` импортирует только `StorageServices`, а не SQLAlchemy/ORM/concrete repositories.
- `StorageServices` собирает User/OAuth/SyncRun repositories и VacancyStore.
- OAuth helpers работают через unified repository с временным legacy dual-write.
- `VacancyStore` нормализует provider payload, но SQL-запросы выполняет `VacancyRepository`.
- External sync worker пишет lifecycle через `SyncRunRepository`, а heartbeat — через `SyncWorkerRepository`.
- Repositories возвращают immutable User/OAuth/Vacancy/Source/SyncRun records, а не session-bound ORM objects.

## Migrations 20260804_0002 — 20260809_0006

Migration `20260804_0002` выполняет:

1. создание `users`, `oauth_connections`, `sync_runs`;
2. копирование legacy OAuth rows без расшифровки/изменения tokens;
3. временное переименование старой `vacancies`;
4. создание canonical `vacancies` и `vacancy_source_records`;
5. backfill canonical row для каждой source vacancy;
6. сохранение source row IDs, raw JSON и search fields;
7. выравнивание PostgreSQL sequence после копирования explicit source IDs;
8. удаление только временной vacancy table после успешного копирования.

Migration поддерживает SQLite и PostgreSQL. Downgrade восстанавливает прежнюю таблицу `vacancies`, но в production downgrade без backup запрещён.

### Migration 20260807_0003

1. создаёт таблицу `sync_workers` для heartbeat внешних worker-процессов;
2. завершает legacy `running` runs нейтральной ошибкой `WorkerRestarted`;
3. добавляет partial unique index, запрещающий более одного `queued/running` run на source;
4. оставляет cached vacancies без изменений;
5. поддерживает SQLite и PostgreSQL, а downgrade удаляет только worker heartbeat/index.


### SEARCH-002 migration 20260809_0006

DATA-002 уже создал relationship `Vacancy 1 — * VacancySourceRecord`, а SEARCH-001 добавил canonical fields. SEARCH-002 revision `20260809_0006` добавляет nullable `dedup_key` и `dedup_version` в обе таблицы и non-unique lookup indexes. Existing `fingerprint` сохраняет прежнюю source-identity роль; исторический backfill dedup metadata не выполняется. Controlled downgrade удаляет только новые indexes/columns после verified backup.

## Совместимость

- Текущие OAuth sessions продолжают использовать provider external ID.
- Текущие templates получают прежние dict keys (`name`, `first_name`, `access_token` и т. д.).
- Публичный API `VacancyStore` не меняется.
- Маршрут и фильтры не меняются; одна карточка может показывать несколько provider sources.
- Existing PostgreSQL rows переходят на candidate revision `20260809_0006` при deploy; business vacancy/OAuth data не переписываются migration 0006.

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

1. `python scripts/manage_db.py upgrade` должен применить `20260809_0006`;
2. `/health/ready` должен показать `current_revision=expected_revision=20260809_0006`;
3. `/`, `/vacancies/internal`, OAuth dashboard и публичный Trudvsem status должны работать;
4. legacy OAuth connection, если он существует, должен остаться доступным;
5. `cached_total` до и после restart должен сохраниться;
6. Multi-source smoke должен показать одну карточку с несколькими source links для доказанного duplicate и раздельные карточки для конфликтующих roles.
7. web process не должен создавать Trudvsem daemon thread; existing sync checkpoint/cache сохраняются.

## Rollback

- Не удалять PostgreSQL.
- Application rollback допустим с сохранением additive columns `0006`; старый код их игнорирует.
- Предпочтительный rollback — restore backup/new database + переключение `DATABASE_URL`.
- Controlled `alembic downgrade 20260808_0005` выполнять только после verified backup и после развертывания совместимого старого кода.

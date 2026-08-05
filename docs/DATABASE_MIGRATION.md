# PostgreSQL и Alembic — production runbook

## 1. Текущее состояние

- `DATA-001` подтверждён: production PostgreSQL 17, revision `20260804_0001`, persistence после restart.
- `DATA-002` добавляет revision `20260804_0002` и ожидает GitHub/Render verification.
- `DATABASE_URL` хранится только в окружении.
- `TOKEN_ENCRYPTION_KEY` нельзя менять при наличии OAuth connections.

## 2. Revision history

### 20260804_0001

- legacy tables `accounts`, `hh_accounts`, source-only `vacancies`;
- indexes/search backfill;
- adoption старого SQLite.

### 20260804_0002

- `users`;
- unified `oauth_connections`;
- canonical `vacancies`;
- provider `vacancy_source_records`;
- `sync_runs`;
- copy legacy OAuth rows без расшифровки tokens;
- conversion source-only vacancy rows в canonical/source relationship.

Legacy `accounts`/`hh_accounts` пока сохраняются для controlled rollback; HH/SuperJob writes временно зеркалируются туда repository-транзакцией.

## 3. CI

GitHub Actions поднимает PostgreSQL 17 и проверяет:

- upgrade всех revisions;
- migration seeded legacy PostgreSQL `0001 -> 0002`;
- `alembic check` на SQLite/PostgreSQL;
- User/OAuth/SyncRun repositories и storage boundaries;
- canonical/source vacancy round-trip и serial sequence continuity;
- OAuth copy + temporary legacy dual-write;
- persistence после Engine recreation;
- отсутствие реальных external API calls.

## 4. Deploy DATA-002

Start command:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

Ожидаемая строка:

```text
Database ready: backend=postgresql, persistent=True, configured=True, revision=20260804_0002
```

Migration error должен остановить deploy до Gunicorn.

## 5. Проверка

### Health

```text
status = ok
database.ok = true
database.backend = postgresql
database.persistent = true
database.configured = true
database.revision = 20260804_0002
```

### Smoke

```text
/
/privacy
/ai-career
/resume-builder
/vacancies
/vacancies/internal
/dashboard
/trudvsem/status
```

### Compatibility

- OAuth HH/SJ connection остаётся доступным после migration.
- Поиск показывает прежние vacancy payloads.
- `cached_total` не сбрасывается.
- После нового Trudvsem run `/trudvsem/status` содержит `persisted_run`.

### Persistence

1. Запомнить `cached_total` и existing connection state.
2. Restart/redeploy.
3. Проверить revision 0002 и сохранность значений.
4. Повторный deploy не должен повторно копировать/дублировать rows.

## 6. Legacy SQLite import

```bash
DATABASE_URL='postgresql+psycopg://...' \
python scripts/import_legacy_sqlite.py --source /secure/path/app.db
```

DATA-002 importer:

- пишет SuperJob/HH rows в `oauth_connections`;
- сохраняет encrypted tokens;
- пишет vacancies через canonical/source repository;
- не хранит source file в GitHub.

## 7. Rollback

### Application rollback

Не удалять PostgreSQL. Старый application commit ожидает schema 0001 и не должен запускаться поверх 0002 без controlled rollback.

### Data rollback

Предпочтительно:

1. backup/clone database;
2. выполнить downgrade/restore на clone;
3. проверить приложение;
4. переключить `DATABASE_URL`.

Не выполнять `alembic downgrade 20260804_0001` на единственной production database без backup.

### Diagnostic fallback

Удаление `DATABASE_URL` включает SQLite, но это не production solution.

## 8. Критерии DATA-002 «ВЫПОЛНЕНО»

- GitHub Actions зелёный;
- PostgreSQL integration test не skipped;
- `/health` revision `20260804_0002`;
- OAuth/search smoke без 500;
- existing rows сохранены;
- restart persistence подтверждён;
- `alembic check` чистый;
- docs/plan обновлены.

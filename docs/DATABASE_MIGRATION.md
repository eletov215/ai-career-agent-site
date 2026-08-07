# PostgreSQL и Alembic — production runbook

| Поле | Значение |
|---|---|
| Текущая revision | `20260807_0003` |
| PostgreSQL | 17 |
| Последний пакет schema | SYNC-001 |
| Статус | НУЖНА ПРОВЕРКА НА GITHUB/RENDER |

## 1. Текущее состояние

- DATA-001/002 подтверждены на production PostgreSQL.
- DATA-002 schema revision: `20260804_0002`.
- SYNC-001 candidate добавляет `20260807_0003`.
- `DATABASE_URL` хранится только в environment.
- `TOKEN_ENCRYPTION_KEY` нельзя менять при наличии OAuth connections.

## 2. Revision history

### 20260804_0001

- legacy `accounts`, `hh_accounts`, source-only `vacancies`;
- indexes/search backfill;
- adoption старого SQLite.

### 20260804_0002

- `users`;
- unified `oauth_connections`;
- canonical `vacancies`;
- `vacancy_source_records`;
- `sync_runs`;
- legacy OAuth/vacancy conversion.

### 20260807_0003

- закрывает legacy `sync_runs.status=running` как `failed/WorkerRestarted` перед включением нового constraint;
- создаёт partial unique index `uq_sync_runs_active_source` для `queued/running`;
- создаёт `sync_workers` heartbeat table;
- не изменяет vacancy/user/OAuth rows;
- поддерживает SQLite/PostgreSQL downgrade.

## 3. CI

GitHub Actions поднимает PostgreSQL 17 и проверяет:

- upgrade всех revisions до `20260807_0003`;
- migration metadata и `alembic check`;
- PostgreSQL integration;
- legacy running-run cleanup;
- active-run constraint;
- queue/worker repositories;
- encrypted backup/restore в отдельную DB;
- полный pytest без внешнего provider network.

## 4. Deploy SYNC-001

Для существующего Render service Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Ожидаемая строка/health:

```text
Database ready: backend=postgresql, persistent=True, configured=True, revision=20260807_0003
```

Migration error должен остановить deploy до запуска supervisor/Gunicorn.

## 5. Проверка

### Health

```text
status = ok
database.ok = true
database.backend = postgresql
database.persistent = true
database.configured = true
database.revision = 20260807_0003
migrations.current_revision = 20260807_0003
migrations.expected_revision = 20260807_0003
```

### Sync schema

В diagnostics mode:

- queued run сохраняется между requests/process restarts;
- active source имеет максимум один `queued/running` row;
- worker heartbeat появляется в `sync_workers`;
- completed run сохраняет processed/saved/cursor/terminal status.

### Application smoke

```text
/
/privacy
/ai-career
/resume-builder
/vacancies/internal
/health/live
/health/ready
/api/sources/trudvsem/status
```

## 6. Legacy SQLite import

```bash
DATABASE_URL='postgresql+psycopg://...' \
python scripts/import_legacy_sqlite.py --source /secure/path/app.db
```

Importer пишет OAuth connections и vacancy cache через repositories. `sync_workers` импортировать не нужно; это ephemeral operational state.

## 7. Rollback

### Application rollback без downgrade

- остановить external worker;
- закрыть queued/running rows как failed;
- вернуть предыдущий application commit;
- оставить PostgreSQL на `20260807_0003`, если старый код не конфликтует с дополнительной таблицей/index.

### Schema downgrade

Только после backup/clone:

```bash
python -m alembic downgrade 20260804_0002
```

Downgrade удаляет `sync_workers` и active-run index. Production database не downgrade-ится без verified backup.

## 8. Критерии SYNC-001 schema verification

- GitHub PostgreSQL migration/integration зелёные;
- Render `/health/ready` revision `20260807_0003`;
- worker heartbeat записывается;
- queue survives process boundary;
- one-active-run constraint работает;
- redeploy не повреждает vacancy cache;
- rollback procedure документирована.

# AI Career Agent — SYNC-001 runbook

| Поле | Значение |
|---|---|
| Документ | SYNC001_RUNBOOK |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Пакет | SYNC-001 |
| Migration | `20260807_0003` |

## 1. Назначение

Runbook описывает запуск, диагностику и rollback внешней синхронизации Trudvsem после удаления daemon thread из Gunicorn.

## 2. Компоненты

```text
app.py
  -> читает PostgreSQL vacancy cache
  -> создаёт queued SyncRun

scripts/trudvsem_sync_worker.py
  -> heartbeat в sync_workers
  -> claim queued SyncRun
  -> provider HTTP
  -> vacancy upsert
  -> terminal SyncRun

scripts/sync_trudvsem.py
  -> one-shot/manual CLI

scripts/start_runtime.py
  -> Render staging supervisor: Gunicorn + worker sibling processes
```

## 3. Конфигурация

| Переменная | Default | Назначение |
|---|---:|---|
| `TRUDVSEM_SYNC_ENABLED` | production: `true` | Включить external worker |
| `TRUDVSEM_SYNC_INTERVAL` | `1800` | Freshness interval cache |
| `TRUDVSEM_SYNC_ITEMS` | `300` | Максимум вакансий на run |
| `TRUDVSEM_SYNC_BATCH` | `10` | Размер API batch |
| `TRUDVSEM_SYNC_POLL_SECONDS` | `15` | Poll durable queue |
| `TRUDVSEM_SYNC_STALE_SECONDS` | `900` | Закрытие abandoned running run |
| `TRUDVSEM_WORKER_HEARTBEAT_SECONDS` | `15` | Worker heartbeat interval |
| `SYNC_SECRET` | без default | Machine endpoint `/sync/trudvsem` |

Секреты не передаются в command line и не входят в ZIP/GitHub.

## 4. Команды

### 4.1 Поставить durable job в очередь

```bash
python scripts/sync_trudvsem.py --enqueue-only --trigger manual-cli
```

### 4.2 Выполнить один run

```bash
python scripts/sync_trudvsem.py --trigger manual-cli
```

### 4.3 Запустить long-running worker

```bash
python scripts/trudvsem_sync_worker.py
```

### 4.4 Выполнить один worker cycle

```bash
python scripts/trudvsem_sync_worker.py --once
```

### 4.5 Docker Compose

```bash
docker compose --env-file .env --profile sync up -d sync-worker
```

## 5. Render staging

Для существующего Render web service Start Command должен быть:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

На free staging worker является отдельным OS process внутри того же service container, а не thread/worker внутри Gunicorn. На будущем VPS он запускается отдельным Compose service.

## 6. Проверка состояния

### 6.1 Health

```text
/health/live
/health/ready
/health
```

Ожидаемая revision: `20260807_0003`.

### 6.2 Public status

```text
/api/sources/trudvsem/status
```

Ответ не должен содержать internal error, worker ID, database details или credentials.

### 6.3 Diagnostic status

При временно включённых `DEBUG_DIAGNOSTICS` и `DIAGNOSTICS_SECRET`:

```text
/trudvsem/status
```

Ожидаемые поля:

```text
worker_mode = external_process
worker_alive = true
workers[] содержит heartbeat
queued/running отражают persisted SyncRun
```

### 6.4 Machine enqueue

```bash
curl -X POST \
  -H "X-Sync-Secret: $SYNC_SECRET" \
  https://<host>/sync/trudvsem
```

Ожидается HTTP `202`, `run_id`, status `queued` или существующий active run.

## 7. Ошибки и восстановление

- provider timeout переводит run в `failed`, но существующий cache не удаляется;
- PostgreSQL advisory lock не позволяет двум workers выполнять source одновременно;
- unique partial index не позволяет двум active runs для одного source;
- если worker погиб, run закрывается после `TRUDVSEM_SYNC_STALE_SECONDS`;
- новый worker продолжает queue после redeploy;
- public route не показывает internal error message.

## 8. Rollback

1. Остановить external worker/supervisor.
2. Закрыть active queued/running rows как failed через maintenance command/SQL.
3. Вернуть предыдущий application commit.
4. Не выполнять Alembic downgrade без проверенного backup.
5. Если downgrade обязателен, сначала убедиться, что `sync_workers` не нужен и нет active queue.

Revision `20260807_0003` обратно совместима с чтением старого vacancy cache; сама таблица вакансий не меняется.

## 9. Критерии завершения

Пакет закрывается только после зелёного CI и Render проверки из `docs/SYNC001_VERIFICATION_STATUS.md`.

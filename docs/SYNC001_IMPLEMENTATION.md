# AI Career Agent - SYNC-001: внешний worker синхронизации Trudvsem

| Поле | Значение |
|---|---|
| Документ | SYNC001_IMPLEMENTATION |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Пакет | `SYNC-001` |
| Статус | НУЖНА ПРОВЕРКА НА GITHUB/RENDER |
| Рабочая основа | `ai-career-agent-site-main (4).zip`, подтверждённый актуальный `main` после INFRA-PREP-001 |
| Результирующий архив | `ai-career-agent-site-main-19-sync-001-external-worker-v1.4.1.zip` |
| Alembic revision | `20260807_0003` |
| Следующий gate | GitHub Actions, Render migration/startup, worker heartbeat и queue-to-terminal smoke |

> Код пакета подготовлен и проверен доступными локальными тестами. Статус «ВЫПОЛНЕНО» не устанавливается до зелёного CI и проверки внешнего worker-процесса на Render.

## 1. Цель и границы

Цель SYNC-001 - удалить синхронизацию «Работы России» из жизненного цикла Flask/Gunicorn и сделать её durable, повторяемой и безопасной при нескольких web-запросах или процессах.

Пакет включает:

- удаление daemon thread, `Event`, process-local progress и `before_request` worker startup из `app.py`;
- durable queue на базе `sync_runs`;
- отдельный long-running worker и one-shot CLI;
- cross-process execution lock;
- persisted heartbeat worker-процесса;
- stale-run recovery;
- интеграцию с Render free staging и Docker Compose;
- migration `20260807_0003`, tests, CI и runbook.

Пакет не включает:

- очистку закрытых или устаревших вакансий;
- полную cursor/watermark/reconciliation policy;
- новый UI;
- перенос production на VPS;
- изменение HH, Reed или SuperJob.

Эти задачи относятся к `SYNC-002`, `SEARCH-*` и предрелизному инфраструктурному блоку.

## 2. Архитектура до и после

### 2.1 До SYNC-001

```text
HTTP request -> Flask/Gunicorn
             -> before_request
             -> daemon threading.Thread
             -> Trudvsem HTTP API
             -> process-local Event/Lock/progress
             -> PostgreSQL vacancy cache
```

Основные риски:

- жизненный цикл worker зависел от Gunicorn;
- restart web-процесса мог оборвать run;
- несколько web workers могли создать несколько threads;
- queue/progress частично находились в памяти;
- provider HTTP находился внутри web runtime.

### 2.2 После SYNC-001

```text
HTTP request -> Flask/Gunicorn -> PostgreSQL vacancy cache
                              -> idempotent enqueue in sync_runs

external worker -> claim queued run
                -> advisory lock / local lockfile
                -> Trudvsem HTTP API
                -> vacancy upsert
                -> durable SyncRun progress/result
                -> sync_workers heartbeat
```

Web-процесс больше не импортирует `TrudvsemProvider`, не создаёт thread и не выполняет Trudvsem provider HTTP.

## 3. Реализованные компоненты

| Компонент | Назначение |
|---|---|
| `services/trudvsem_sync.py` | Flask-independent application service: enqueue, due check, execution, progress и stale recovery |
| `services/sync_lock.py` | PostgreSQL session advisory lock или SQLite-compatible exclusive lockfile |
| `scripts/trudvsem_sync_worker.py` | Long-running worker с polling, heartbeat и graceful shutdown |
| `scripts/sync_trudvsem.py` | One-shot execution или enqueue-only CLI |
| `scripts/start_runtime.py` | Render free supervisor: Gunicorn и worker как sibling OS processes |
| `repositories/sync_runs.py` | Durable enqueue/claim/heartbeat/finish и active-run lookup |
| `repositories/sync_workers.py` | Persistent worker heartbeat, liveness и stale-record cleanup |
| `models/sync_worker.py` | ORM-модель worker heartbeat |
| `20260807_0003_external_sync_worker.py` | Additive migration для active-run constraint и `sync_workers` |
| `compose.yaml` | Отдельный `sync-worker` service в profile `sync` |
| `render.yaml` | Migration + runtime supervisor для текущего free web service |
| `tests/test_sync_worker.py` | Queue, lock, execution, failure preservation, heartbeat, stale recovery и migration tests |

## 4. Durable queue и SyncRun

Основной жизненный цикл:

```text
queued -> running -> succeeded
                  -> failed
```

`SyncRunRepository.enqueue()` идемпотентен. Partial unique index:

```text
uq_sync_runs_active_source
WHERE status IN ('queued', 'running')
```

гарантирует не более одного активного run на source. При конкурентных enqueue-запросах проигравшая транзакция возвращает уже существующий active run.

Worker обновляет:

- `status`;
- `processed`;
- `saved`;
- `cursor`;
- `updated_at`;
- terminal status и ограниченную ошибку.

Public status не возвращает raw upstream body, credentials, worker ID или internal error message.

## 5. Защита от параллельного выполнения

Используются два уровня:

1. **Database active-run constraint** - блокирует несколько `queued/running` rows для одного source.
2. **Execution lock**:
   - PostgreSQL: `pg_try_advisory_lock` удерживается выделенным соединением на время run;
   - SQLite local/test: lockfile создаётся атомарно через `O_EXCL` и восстанавливается после stale threshold.

Lock проверяется до claim/execution, поэтому два внешних worker-процесса не выполняют один источник одновременно.

## 6. Worker heartbeat и recovery

Таблица `sync_workers` хранит:

- worker ID;
- source;
- `idle`/`running` status;
- current run ID;
- started/heartbeat timestamps;
- ограниченные details без секретов.

Worker:

1. публикует heartbeat;
2. закрывает abandoned `running` rows после `TRUDVSEM_SYNC_STALE_SECONDS`;
3. выполняет queued job или запускает scheduled run при устаревшем cache;
4. удаляет heartbeat при штатном завершении.

Diagnostic status использует расширенный liveness window, чтобы долгий provider request не создавал ложное состояние «worker dead».

## 7. Scheduling и ошибки

Freshness определяется возрастом persisted Trudvsem cache:

```text
TRUDVSEM_SYNC_INTERVAL=1800
```

При наличии последнего successful run worker передаёт его `finished_at` как `modifiedFrom`. Полная incremental cleanup policy остаётся задачей `SYNC-002`.

При ошибке внешнего API:

- run переводится в `failed`;
- старый vacancy cache не удаляется;
- сохраняются `error_type` и ограниченное message;
- long-running worker продолжает polling;
- one-shot CLI возвращает ненулевой exit code.

## 8. Deployment modes

### 8.1 Render free staging

Для существующего Render web service требуется Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Supervisor запускает два sibling OS processes:

```text
Gunicorn
Trudvsem external worker
```

Worker больше не находится внутри Gunicorn. Общий container restart остаётся временным ограничением free staging до `HOST-001`.

### 8.2 Docker/VPS

Worker запускается отдельным service:

```bash
docker compose --env-file .env --profile sync up -d db migrate web sync-worker
```

Service не публикует порт, использует backend network и зависит от healthy DB и successful migration.

## 9. Влияние на сайт

| Область | Результат |
|---|---|
| UI | Визуально не меняется |
| Trudvsem search | Читает PostgreSQL cache; provider HTTP не блокирует page request |
| Пустой/устаревший cache | Web создаёт один durable job и показывает нейтральный статус |
| Ошибка upstream | Последний cache остаётся доступным |
| Restart web | Queue, run state и cache остаются в PostgreSQL |
| HH/Reed/SuperJob | Не изменены |
| OAuth/PDF | Не изменены |
| Database | Additive migration `20260807_0003`; vacancy/OAuth rows не переписываются |

## 10. Конфигурация

| Переменная | Default | Назначение |
|---|---:|---|
| `TRUDVSEM_SYNC_ENABLED` | production: `true` | Kill switch для enqueue и worker |
| `TRUDVSEM_SYNC_INTERVAL` | `1800` | Freshness interval cache |
| `TRUDVSEM_SYNC_ITEMS` | `300` | Максимум вакансий на run |
| `TRUDVSEM_SYNC_BATCH` | `10` | Размер API batch |
| `TRUDVSEM_SYNC_POLL_SECONDS` | `15` | Poll durable queue |
| `TRUDVSEM_SYNC_STALE_SECONDS` | `900` | Порог abandoned `running` run |
| `TRUDVSEM_WORKER_HEARTBEAT_SECONDS` | `15` | Heartbeat interval |
| `SYNC_SECRET` | без default | Machine endpoint `/sync/trudvsem` |

`TRUDVSEM_SYNC_ENABLED=0` безопасно отключает новые jobs/worker; web продолжает читать существующий cache.

## 11. Локальные доказательства

```text
pytest: 115 passed, 6 skipped
SYNC-001 tests: 10 passed
SQLite migration 0001 -> 0002 -> 0003: passed
Alembic check: No new upgrade operations detected
SQLite downgrade 0003 -> 0002 -> upgrade 0003: passed
repository hygiene: passed
compileall: passed
INFRA manifest: passed
document structure: passed
workflow YAML parse: passed
shell syntax: passed
```

Локальные skips относятся к Flask-dependent modules, Psycopg и реальному PostgreSQL service, отсутствующим в текущем изолированном окружении. GitHub Actions устанавливает production dependencies и запускает PostgreSQL 17.

Docker CLI недоступен локально; Compose validation, image build и runtime smoke должны быть подтверждены GitHub Actions.

## 12. Ограничения и rollback

### Ограничения

- Render free объединяет web и worker в одном container, хотя процессы независимы.
- `SYNC-002` должен добавить stale-vacancy cleanup и полную incremental freshness policy.
- rate-limit `memory://` остаётся рассчитанным на текущий один Gunicorn worker.

### Rollback

1. Установить `TRUDVSEM_SYNC_ENABLED=0`.
2. Остановить worker/supervisor или вернуть прежний Start Command.
3. Откатить application commit; schema `20260807_0003` можно оставить, она additive.
4. Alembic downgrade выполнять только после verified backup и только при явной необходимости.
5. Старый vacancy cache не удалять.

## 13. Критерии завершения

SYNC-001 закрывается только после:

1. зелёного GitHub Actions;
2. Render revision `20260807_0003`;
3. `health/live`, `health/ready` и `health` = `200`;
4. свежего persisted worker heartbeat;
5. protected enqueue `202` и перехода run `queued -> running -> terminal`;
6. search/cache smoke без provider I/O в web request;
7. redeploy/recovery smoke без потери cache.

Следующий пакет после подтверждения - `SYNC-002`.


## 14. Рекомендуемый rollout

1. Создать ветку `sync-001-external-worker` от актуального `main`.
2. Загрузить полный проект с сохранением dotfiles.
3. Дождаться зелёных шагов GitHub Actions, включая `Verify SYNC-001 external worker controls`, PostgreSQL migration/integration, SEC/OPS и полный pytest.
4. Объединить Pull Request только после зелёного CI.
5. На Render проверить фактический Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

6. После deploy подтвердить revision `20260807_0003`, worker heartbeat, очередь `queued -> running -> terminal`, cache/search smoke и восстановление после redeploy.
7. При проблеме использовать kill switch `TRUDVSEM_SYNC_ENABLED=0` и rollback из раздела 12.

## 15. Комплект поставки

- полный ZIP проекта `ai-career-agent-site-main-19-sync-001-external-worker-v1.4.1.zip`;
- PLAN_CURRENT `1.4.1`;
- PROJECT_PASSPORT `2.15`;
- этот implementation report;
- отдельный verification checklist;
- source audit и инструкция по замене источников.

Статус пакета до завершения внешней проверки остаётся `НУЖНА ПРОВЕРКА`.

# AI Career Agent — статус проверки SYNC-001

| Поле | Значение |
|---|---|
| Документ | SYNC001_VERIFICATION_STATUS |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Пакет | SYNC-001 |
| Статус | НУЖНА ПРОВЕРКА НА GITHUB/RENDER |
| Migration | `20260807_0003` |

## 1. Что реализовано

- daemon thread и process-local queue/state удалены из `app.py`;
- durable idempotent queue на `sync_runs`;
- one-active-run database constraint;
- external worker и one-shot CLI;
- PostgreSQL advisory lock / SQLite lockfile;
- persisted worker heartbeat;
- migration `20260807_0003`;
- Render runtime supervisor;
- Compose `sync-worker` service;
- CI и regression tests;
- source/docs sync до PLAN_CURRENT 1.4.1 и passport 2.15.

## 2. Локальные доказательства

| Проверка | Результат |
|---|---|
| Доступный pytest | 116 passed, 6 skipped |
| SYNC-001 unit/migration tests | 9 passed |
| SQLite migration 0001→0002→0003 | ПРОЙДЕНО |
| Alembic check | No new upgrade operations detected |
| SQLite downgrade/upgrade 0003 | ПРОЙДЕНО |
| INFRA manifest validator | ПРОЙДЕНО |
| YAML parse | ПРОЙДЕНО |

Локальные skips относятся к Flask/Psycopg/PostgreSQL service, отсутствующим в sandbox. В GitHub Actions эти тесты обязаны выполняться.

## 3. GitHub Actions

Ожидаемые зелёные шаги:

```text
Apply test database migrations
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEC-001 security controls
Verify OPS-001 observability controls
Verify SYNC-001 external worker controls
Verify PostgreSQL encrypted backup and restore
Verify INFRA-001 manifests, probe and document structure
Validate Docker Compose
Build container targets
Smoke-test runtime image
Run tests
```

Статус до подтверждения: `НУЖНА ПРОВЕРКА`.

## 4. Render deploy

### 4.1 Обязательное изменение Start Command

Для существующего Render service вручную установить:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

`render.yaml` содержит это значение, но вручную созданный service может не применить Blueprint автоматически.

### 4.2 Health

```text
/health/live  -> 200
/health/ready -> 200
/health       -> 200
revision      -> 20260807_0003
```

### 4.3 Логи процессов

Application logs должны показать:

```text
runtime_supervisor: Starting trudvsem-worker
runtime_supervisor: Starting gunicorn
trudvsem_sync_worker: worker started
```

Не должно быть startup loop, migration error или нескольких параллельных workers.

## 5. Worker heartbeat

Временно включить diagnostics и открыть `/trudvsem/status` с `X-Diagnostics-Secret`.

Ожидается:

```text
worker_mode: external_process
worker_alive: true
workers: минимум один свежий heartbeat
```

После проверки diagnostics снова отключить.

## 6. Queue-to-terminal smoke

1. Вызвать protected `POST /sync/trudvsem` с `X-Sync-Secret`.
2. Получить HTTP `202`, `run_id`, status `queued`.
3. Проверить diagnostic status: queued → running.
4. Дождаться terminal status `succeeded` или контролируемого `failed`.
5. При success проверить `processed/saved` и новый cache age.
6. При upstream failure убедиться, что старый `cached_total` не обнулился.

## 7. Search smoke

- `/vacancies/internal` открывается без HTTP 500;
- Trudvsem читается из cache;
- cache miss только ставит job в очередь;
- page request не ждёт provider API;
- public status остаётся sanitised.

## 8. Redeploy/recovery smoke

- выполнить обычный redeploy;
- `/health/ready` снова `200` и revision `20260807_0003`;
- worker heartbeat появляется заново;
- cache сохраняется;
- abandoned run закрывается после stale threshold и не блокирует последующие jobs;
- два одновременных enqueue возвращают один active run.

## 9. Решение по статусу

| Условие | Статус |
|---|---|
| Код и локальные проверки | ПРОЙДЕНО |
| GitHub CI | ОЖИДАЕТСЯ |
| Render migration/startup | ОЖИДАЕТСЯ |
| Worker heartbeat | ОЖИДАЕТСЯ |
| Queue-to-terminal | ОЖИДАЕТСЯ |
| Search/redeploy smoke | ОЖИДАЕТСЯ |

После всех подтверждений `SYNC-001 → ВЫПОЛНЕНО`, следующий пакет — `SYNC-002`.

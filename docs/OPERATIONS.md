# AI Career Agent - эксплуатация и наблюдаемость OPS-001

**Пакет:** `OPS-001`  
**Статус:** OPS-001 ВЫПОЛНЕНО; SYNC-001 НУЖНА ПРОВЕРКА  
**Последнее обновление:** 07 августа 2026

## 1. Цель

OPS-001 создаёт минимальный vendor-neutral operational layer до выбора VPS:

- структурированные и безопасные логи в stdout;
- correlation ID для каждого HTTP-запроса;
- bounded HTTP/provider metrics;
- последние sanitised ошибки и optional alert webhook;
- отдельные liveness/readiness endpoints;
- encrypted backup, manifest, integrity verification и restore drill;
- runbook для диагностики, аварий и rollback.

OPS-001 не менял schema. SYNC-001 добавил migration `20260807_0003`; candidate SYNC-002 добавляет `20260807_0004`. После его deploy health/readiness должны показывать revision `20260807_0004`.

## 2. Логи

### Production

По умолчанию:

```text
LOG_FORMAT=json
LOG_LEVEL=INFO
SERVICE_NAME=ai-career-agent
APP_VERSION=<commit/tag>
```

Каждая строка - один JSON-объект с bounded полями:

```json
{
  "timestamp": "2026-08-05T10:00:00.000+00:00",
  "level": "INFO",
  "service": "ai-career-agent",
  "environment": "production",
  "version": "<commit>",
  "logger": "http.access",
  "message": "HTTP request completed",
  "request_id": "...",
  "method": "GET",
  "endpoint": "health_ready",
  "route": "/health/ready",
  "status_code": 200,
  "duration_ms": 12.5
}
```

Логи не должны содержать:

- request body или query string;
- cookie и session content;
- OAuth/API tokens;
- database URL/password;
- resume text, cover-letter text или user-entered search text;
- raw provider response bodies.

`LogSanitizer` удаляет configured secrets, bearer/basic credentials, credentials in URLs, query strings и значения чувствительных mapping keys.

### Local development

```text
LOG_FORMAT=text
LOG_LEVEL=DEBUG
```

Text-format сохраняет `request_id` и проходит тот же sanitizer.

## 3. Correlation ID

- Клиент может прислать безопасный `X-Request-ID` длиной 8-128 символов.
- Недопустимое значение игнорируется, приложение создаёт UUID.
- Ответ всегда содержит `X-Request-ID`.
- Ошибки и provider metrics используют тот же ID.

При обращении в поддержку пользователь может сообщить `X-Request-ID`; содержимое запроса для этого не требуется.

## 4. Health endpoints

### `GET /health/live`

Проверяет, что web-process отвечает. Не зависит от PostgreSQL.

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "ai-career-agent",
  "version": "...",
  "request_id": "...",
  "uptime_seconds": 120
}
```

### `GET /health/ready`

Проверяет:

- соединение с PostgreSQL;
- текущую Alembic revision;
- совпадение revision с `CURRENT_REVISION`.

Возвращает HTTP `200` при готовности и `503` при недоступной базе или несовпадении migration.

### `GET /health`

Совместимый alias readiness для существующего monitoring.

`render.yaml` использует `/health/ready`.

## 5. Metrics и diagnostics

In-process registry хранит bounded данные:

- HTTP calls, 2xx/4xx/5xx, p50/p95 latency;
- provider calls/success/failure/timeouts/latency;
- последние 50 sanitised ошибок;
- alert delivery counters.

Полный snapshot доступен только через:

```text
GET /ops/status
```

Требуются одновременно:

```text
DEBUG_DIAGNOSTICS=1
DIAGNOSTICS_SECRET=<long random value>
X-Diagnostics-Secret: <same value>
```

Без этого маршрут возвращает `404`.

Ограничение: metrics и recent errors process-local. Для нескольких workers/instances потребуется shared exporter/storage в INFRA/HOST.

## 6. Alert webhook

Необязательная конфигурация:

```text
OPS_ALERT_WEBHOOK_URL=https://alerts.example/...
OPS_ALERT_WEBHOOK_TOKEN=<optional bearer token>
OPS_ALERT_TIMEOUT_SECONDS=3
OPS_ALERT_MIN_LEVEL=ERROR
```

Production требует HTTPS URL без credentials и fragment. Ошибки отправляются через bounded daemon queue. Payload содержит только service/environment/version/timestamp/level/request_id/event/error_type и sanitised message.

### Тест доставки

Вариант CLI:

```bash
APP_ENV=production \
OPS_ALERT_WEBHOOK_URL='https://...' \
OPS_ALERT_WEBHOOK_TOKEN='...' \
python scripts/send_test_alert.py
```

Вариант diagnostics endpoint:

```text
POST /ops/alerts/test
X-Diagnostics-Secret: ...
```

Пакет нельзя перевести в `ВЫПОЛНЕНО`, пока тестовый alert фактически не получен выбранным каналом.

## 7. Provider metrics

Инструментированы:

- HeadHunter vacancy search;
- SuperJob vacancy search;
- Reed vacancy search;
- Trudvsem sync batches;
- university-logo lookup.

Metrics не содержат keywords, filters или provider payload. Ошибка фиксируется по типу и, если безопасно доступен, HTTP status.

## 8. Operational checklist после deploy

1. `/health/live` -> `200`.
2. `/health/ready` -> `200`, revision `20260807_0004`.
3. `/health` -> тот же readiness result.
4. Ответы имеют `X-Request-ID`.
5. Render logs содержат JSON и не содержат token/query/body.
6. Vacancy search создаёт provider metrics без пользовательских параметров.
7. Diagnostics routes закрыты без secret.
8. Test alert доставлен, если webhook configured.
9. Backup создан, verify пройден, restore выполнен в отдельную test DB.
10. Повторный deploy не повреждает данные.

## 9. Ограничения до следующих пакетов

- Alert webhook не настроен по умолчанию.
- Metrics и alert queue process-local.
- Offsite backup schedule не настроен до выбора production VPS.
- Trudvsem daemon thread удалён. External worker heartbeat и queue-to-terminal smoke должны быть подтверждены на Render.
- SEC-001 production smoke завершён; повторяется как regression gate в CI.

## 10. Production restore drill OPS-002/REL-001

Production restore drill перенесён из закрытого базового OPS-001 в обязательный предрелизный `OPS-002/REL-001`. INFRA-PREP уже предоставляет `ops` image с PostgreSQL 17 tools, persistent backup volume и isolated `restore-db`. Production database никогда не используется как restore target.

## 11. SYNC-001 external worker operations

### 11.1 Render staging

Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

`runtime_supervisor` запускает Gunicorn и `trudvsem_sync_worker.py` как sibling OS processes. Worker failure не завершает Gunicorn: supervisor перезапускает worker с задержкой.

### 11.2 VPS/Compose

```bash
docker compose --env-file .env --profile sync up -d sync-worker
```

Web service не должен включать provider I/O. `sync-worker` не публикует порт и использует private backend network.

### 11.3 Operational signals

- `sync_workers.heartbeat_at` — liveness process;
- `sync_runs.status` — queued/running/terminal state;
- `processed/saved/cursor` — progress;
- `error_type` — bounded failure classification;
- public status не содержит error details;
- diagnostic status доступен только с diagnostics secret.

### 11.4 Recovery

- stale running run закрывается после `TRUDVSEM_SYNC_STALE_SECONDS` (default 900);
- PostgreSQL advisory lock исключает параллельный provider run;
- существующий cache не удаляется при failure;
- после redeploy новый worker продолжает durable queue.

Подробности: `docs/SYNC001_RUNBOOK.md`.



## 12. SYNC-002 incremental operations

После candidate deploy revision должна быть `20260807_0004`.

Operational state хранится в `sync_checkpoints`:

- `watermark_at` — committed last complete window;
- `pending_from_at/pending_to_at/pending_offset` — durable continuation;
- `consecutive_failures/next_retry_at` — persistent exponential backoff;
- `last_cleanup_at` — последняя successful TTL/retention cleanup.

Критические проверки:

1. partial run сохраняет `pending_offset`, а следующий run продолжает то же fixed window;
2. failure не меняет committed watermark и не удаляет cache;
3. повторный upsert не создаёт duplicate `(source, external_id)`;
4. explicit provider closed event скрывает vacancy из search;
5. TTL closure выполняется только после полного успешного окна;
6. long-retained closed row purged по retention policy;
7. reactivated source row снова становится active.

Подробности: `docs/SYNC002_RUNBOOK.md`.

## SEARCH-005 operations
Configure `SEARCH_ADMIN_EMAILS`; monitor persistent provider states through `/admin/sources`. The page performs no external probe. Telemetry persistence is non-gating. Application rollback may retain migration 0014.


## AI-001 delta / 1.5.0 / 2026-09-14

Central technical caps are changed through scripts/manage_ai_runtime.py with expected-version, without provider rewrites or web redeploy. Keep AI environment and DB gates closed. Admission/settlement locks never surround HTTP. Unknown outcomes retain conservative costs and global caps survive deleted users.

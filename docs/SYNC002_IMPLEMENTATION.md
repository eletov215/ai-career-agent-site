# AI Career Agent — SYNC-002: инкрементальная загрузка и очистка вакансий Trudvsem

| Поле | Значение |
|---|---|
| Документ | SYNC002_IMPLEMENTATION |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Пакет | SYNC-002 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | `ai-career-agent-site-main (5).zip` — актуальный GitHub `main` после SYNC-001 |
| Candidate revision | `20260807_0004` |
| Следующий gate | GitHub Actions + Render production smoke; затем SEARCH-001 |

Пакет реализован локально и не объявляется выполненным до подтверждения PostgreSQL migration/integration в GitHub Actions и фактического incremental/cleanup поведения на Render.

## 1. Цель и границы

Цель SYNC-002 — развить внешний worker SYNC-001 до полноценной incremental freshness policy:

- получать только записи, изменённые в зафиксированном временном окне;
- продолжать большой change-set с сохранённого offset после нового run/reconnect;
- не создавать дублей при overlap и повторной обработке;
- скрывать явно закрытые и TTL-expired вакансии;
- удалять только давно закрытые source rows после retention;
- не продвигать watermark и не очищать cache при ошибке upstream;
- измерять progress на основании provider `meta.total`.

Пакет не включает cross-source canonical contract, fuzzy dedup, общую пагинацию между источниками или новый UI. Эти задачи остаются в SEARCH-001/002/003.

## 2. Контракт API Trudvsem

Worker использует поддерживаемые API-параметры:

```text
limit
page offset (1-based)
modifiedFrom=<ISO-8601>
modifiedTo=<ISO-8601>
```

Верхняя граница `modifiedTo` фиксируется до первого запроса и сохраняется в PostgreSQL. Это исключает бесконечно движущееся окно, если во время загрузки появляются новые изменения.

## 3. Архитектура

```text
scheduled/manual trigger
        ↓
sync_runs: queued → running
        ↓
sync_checkpoints
  committed watermark
  pending from/to
  pending offset/limit/total
  retry state
        ↓
external worker
  Trudvsem modifiedFrom/modifiedTo
  page N
        ↓
idempotent vacancy source upsert
        ↓
page cursor persisted
        ↓
complete window?
  no  → successful partial run, continue later
  yes → cleanup + watermark commit
```

Ключевой принцип: `watermark_at` меняется только после полного успешного окна. До этого продолжение хранится в `pending_*`.

## 4. Схема данных и migration 0004

Migration `20260807_0004_incremental_sync_cleanup.py`:

1. создаёт `sync_checkpoints`;
2. добавляет в `vacancy_source_records`:
   - `source_modified_at`;
   - `closed_at`;
   - `closed_reason`;
   - `last_seen_run_id`;
3. добавляет индексы по source/status/published и `closed_at`;
4. для каждого source выбирает один последний successful SyncRun и использует его `finished_at` как начальный watermark;
5. поддерживает controlled downgrade до `20260807_0003`.

`ROW_NUMBER() OVER (PARTITION BY source ORDER BY finished_at DESC, id DESC)` делает seed детерминированным даже при одинаковом `finished_at`.

## 5. Persistent checkpoint

`SyncCheckpointRepository` хранит:

| Поле | Назначение |
|---|---|
| `watermark_at` | последняя полностью подтверждённая верхняя граница |
| `pending_from_at` / `pending_to_at` | immutable окно текущего change-set |
| `pending_offset` / `pending_limit` | следующая страница и размер страницы |
| `pending_total` | provider total для progress/continuation |
| `last_success_run_id` / `last_success_at` | последний успешный chunk/window |
| `last_cleanup_at` | момент последнего cleanup |
| `consecutive_failures` | число последовательных ошибок |
| `next_retry_at` | persistent backoff deadline |

Checkpoint остаётся в PostgreSQL после restart/redeploy и включается в backup inventory.

## 6. Incremental window и bootstrap

### 6.1 Обычное окно

```text
from = watermark_at - overlap
  to = current UTC timestamp before request
```

Default overlap — 300 секунд. Повторно пришедшие записи безопасны благодаря уникальному `(source, external_id)` и upsert.

### 6.2 Fresh database/bootstrap

Если watermark отсутствует, создаётся bounded bootstrap-window последних `TRUDVSEM_VACANCY_TTL_DAYS` дней. Оно использует тот же persistent cursor и может продолжаться несколькими runs. После полного завершения `pending_to_at` становится committed watermark.

### 6.3 Continuation

Один run обрабатывает не больше `TRUDVSEM_SYNC_ITEMS`. Если provider total больше лимита:

- run завершается `succeeded`, но `window_complete=false`;
- pending offset сохраняется;
- следующий worker cycle продолжает с него;
- restart/reconnect не сбрасывает continuation;
- committed watermark остаётся прежним до полной загрузки окна.

## 7. Идемпотентный lifecycle upsert

Upsert по `(source, external_id)`:

- повторная страница не создаёт дубль;
- active update очищает `closed_at`/`closed_reason` и реактивирует запись;
- explicit provider closed/deleted/archived/expired переводит source row в `closed`;
- `source_modified_at` хранит timestamp изменения provider;
- `last_seen_run_id` связывает запись с конкретным SyncRun;
- canonical `is_active` пересчитывается по active source rows.

Public search всегда фильтрует `source_status == active`.

## 8. Cleanup policy

Cleanup запускается только после полного успешного окна:

1. **TTL closure:** active Trudvsem rows с `published_at` старше `TRUDVSEM_VACANCY_TTL_DAYS` переводятся в `closed` с reason `published_ttl`.
2. **Retention purge:** source rows, закрытые дольше `TRUDVSEM_CLOSED_RETENTION_DAYS`, удаляются; orphan canonical vacancy удаляется только при отсутствии других source rows.
3. Cleanup counts (`closed`, `purged`) записываются в SyncRun details и structured logs.

Текущий TTL 45 дней намеренно превышает максимальный пользовательский фильтр 30 дней.

## 9. Retry и failure preservation

При provider/network/parse error:

- run получает `failed`;
- pending window/cursor сохраняются;
- watermark и `last_cleanup_at` не продвигаются;
- старый cache не удаляется;
- `consecutive_failures` увеличивается;
- `next_retry_at` вычисляется как bounded exponential backoff:

```text
min(RETRY_MAX, RETRY_BASE × 2^(failures-1))
```

Manual trigger может выполнить осознанный retry, а scheduled worker соблюдает deadline.

## 10. Конфигурация

| Переменная | Default | Назначение |
|---|---:|---|
| `TRUDVSEM_SYNC_INTERVAL` | 1800 | интервал freshness |
| `TRUDVSEM_SYNC_ITEMS` | 300 | максимум items на один run |
| `TRUDVSEM_SYNC_BATCH` | 10 | размер API page |
| `TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS` | 300 | overlap watermark |
| `TRUDVSEM_VACANCY_TTL_DAYS` | 45 | closure старых active rows |
| `TRUDVSEM_CLOSED_RETENTION_DAYS` | 30 | retention закрытых rows |
| `TRUDVSEM_RETRY_BASE_SECONDS` | 60 | начальный retry delay |
| `TRUDVSEM_RETRY_MAX_SECONDS` | 3600 | максимальный retry delay |

Config validation запрещает TTL меньше 31 дня и retry max меньше retry base.

## 11. Изменённые компоненты

| Область | Изменение |
|---|---|
| `models/sync_checkpoint.py` | persistent checkpoint model |
| `models/vacancy.py` | lifecycle fields/indexes |
| `repositories/sync_checkpoints.py` | watermark/cursor/retry repository |
| `repositories/vacancies.py` | lifecycle upsert, close, purge, counts |
| `services/trudvsem_provider.py` | page + total + modified window + lifecycle mapping |
| `services/trudvsem_sync.py` | resumable bootstrap/incremental algorithm |
| `services/vacancy_store.py` | run-aware upsert и cleanup policy |
| `config.py` | SYNC-002 settings/validation |
| `operations/backup.py` | checkpoint table inventory |
| worker/CLI/app diagnostics | checkpoint integration |
| migration `0004` | additive schema |
| CI/tests/docs | отдельный SYNC-002 gate |

## 12. Влияние на сайт

- UI и URL не меняются.
- Trudvsem search продолжает читать PostgreSQL cache.
- Повторные изменения не порождают duplicate cards.
- Closed/TTL-expired records больше не попадают в выдачу.
- Во время provider failure пользователь видит последний успешный cache.
- Diagnostics дополнительно показывают checkpoint, active/closed totals и retry state.
- HH, Reed, SuperJob, OAuth и PDF не изменены.

## 13. Локальные доказательства

```text
full pytest: 130 passed, 6 skipped
SYNC-002 tests: 8 passed
SQLite migration 0001 → 0002 → 0003 → 0004: passed
SQLite downgrade 0004 → 0003 → 0004: passed
Alembic check: no new upgrade operations
repository hygiene: passed
INFRA manifest/document validators: passed
```

Skips относятся к Flask/Psycopg/real PostgreSQL runtime, которые предоставляет GitHub Actions.

## 14. Rollout

1. Создать ветку `sync-002-incremental-cleanup` от актуального main.
2. Загрузить полный архив с dotfiles.
3. Дождаться зелёного `Verify SYNC-002 incremental freshness and cleanup controls`, PostgreSQL migration/integration, backup/restore, container smoke и full pytest.
4. Merge только после зелёного CI.
5. Render применяет migration `20260807_0004`; Start Command не меняется.
6. Проверить `/health/ready`, diagnostics checkpoint, incremental run, terminal cleanup и restart persistence.

## 15. Rollback

1. `TRUDVSEM_SYNC_ENABLED=0` — остановить enqueue/worker.
2. Сохранить текущий cache и backup.
3. Откатить application commit; additive schema `0004` может временно остаться.
4. Downgrade до `0003` выполнять только после verified backup и остановленного worker.
5. При rollback не удалять vacancy cache вручную.

## 16. Статус

```text
SYNC-002 — НУЖНА ПРОВЕРКА
```

Следующий пакет после подтверждения — `SEARCH-001`.

# AI Career Agent — статус проверки SYNC-002

| Поле | Значение |
|---|---|
| Документ | SYNC002_VERIFICATION_STATUS |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Пакет | SYNC-002 |
| Текущий статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260807_0004` |
| Следующий пакет после подтверждения | SEARCH-001 |

## 1. Что уже подтверждено локально

| Проверка | Результат |
|---|---|
| Полный доступный pytest | 130 passed, 6 skipped |
| SYNC-002 unit/migration tests | 8 passed |
| Migration 0004 upgrade | ПРОЙДЕНО |
| Downgrade 0004 → 0003 → 0004 | ПРОЙДЕНО |
| Alembic metadata check | ПРОЙДЕНО |
| Repository hygiene | ПРОЙДЕНО |
| INFRA manifest/document validators | ПРОЙДЕНО |
| Secret/runtime artifact scan | ПРОЙДЕНО |

## 2. Покрытые сценарии

- deterministic checkpoint seed при одинаковом `finished_at`;
- bounded `modifiedFrom`/`modifiedTo` request;
- provider lifecycle active/closed mapping;
- overlap и watermark advance только после complete window;
- resumable bootstrap и incremental cursor;
- cursor persistence после reconnect БД;
- idempotent upsert без дублей;
- exponential retry/backoff без продвижения watermark;
- closed rows скрываются из search;
- TTL closure, retention purge и reactivation;
- backup/restore содержит `sync_checkpoints`.

## 3. Обязательные GitHub Actions

Ожидаются зелёными:

```text
Apply test database migrations
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SYNC-001 external worker controls
Verify SYNC-002 incremental freshness and cleanup controls
Verify PostgreSQL encrypted backup and restore
Verify INFRA manifests
Validate Docker Compose
Build container targets
Smoke-test runtime image
Run tests
```

## 4. Обязательная Render-проверка

### 4.1 Health и migration

```text
/health/ready → HTTP 200
current_revision  = 20260807_0004
expected_revision = 20260807_0004
database.ok       = true
```

### 4.2 Checkpoint

С diagnostics access `/trudvsem/status` должен показать:

- checkpoint существует;
- `pending_from_at < pending_to_at` во время run;
- `pending_offset` изменяется при continuation;
- после complete window `pending=false`;
- `watermark_at` становится равен завершённой upper bound;
- active/closed totals неотрицательны.

### 4.3 Incremental continuation

Для change-set, который не помещается в один run:

1. первый run заканчивается `succeeded` + `window_complete=false`;
2. checkpoint сохраняет `pending_offset`;
3. следующий run начинает с того же offset;
4. после завершения watermark продвигается, duplicate source rows не появляются.

### 4.4 Failure preservation

При контролируемой upstream error:

- run → failed;
- старый `cached_total` остаётся > 0;
- watermark не меняется;
- pending cursor сохраняется;
- `next_retry_at` появляется;
- scheduled worker не создаёт tight retry loop.

### 4.5 Cleanup

Подтвердить на test fixture или controlled test rows:

- explicit closed не возвращается в public search;
- old active row закрывается только после complete successful window;
- purge удаляет только closed row старше retention;
- active update может реактивировать ранее закрытую запись.

### 4.6 Restart

После restart/redeploy:

- checkpoint/watermark/cursor не обнуляются;
- cache остаётся;
- worker продолжает pending window либо остаётся idle;
- вечного `running` run нет.

## 5. Критерий закрытия

SYNC-002 переводится в **ВЫПОЛНЕНО** только после:

1. полностью зелёного GitHub Actions;
2. Render revision `20260807_0004`;
3. production evidence checkpoint/window/watermark;
4. подтверждения retry/cache preservation;
5. подтверждения cleanup/lifecycle;
6. restart persistence.

До этого следующий кодовый пакет не объединяется в main.

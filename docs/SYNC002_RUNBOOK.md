# AI Career Agent — runbook проверки SYNC-002

| Поле | Значение |
|---|---|
| Документ | SYNC002_RUNBOOK |
| Версия | 1.0 |
| Дата | 07 августа 2026 |
| Пакет | SYNC-002 |
| Migration | `20260807_0004` |
| Назначение | GitHub/Render verification и rollback |

## 1. Перед загрузкой

1. Использовать только актуальный `main`/ZIP.
2. Создать ветку:

```text
sync-002-incremental-cleanup
```

3. Не включать `.env`, secrets, databases, dumps, backups, caches, bytecode.
4. Сохранить dotfiles: `.github`, `.gitignore`, `.dockerignore`, `infra/vps/.env.example`.

## 2. GitHub Actions

Commit:

```text
sync: add incremental Trudvsem freshness and cleanup
```

Проверить отдельный шаг:

```text
Verify SYNC-002 incremental freshness and cleanup controls
```

Если падает migration — раскрыть `Apply test database migrations` и `Verify PostgreSQL migrations`. Если падает backup — убедиться, что manifest содержит `sync_checkpoints`.

## 3. Render configuration

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Новые переменные имеют безопасные defaults и не обязательны для старта. Для явной production-конфигурации:

```text
TRUDVSEM_SYNC_INTERVAL=1800
TRUDVSEM_SYNC_ITEMS=300
TRUDVSEM_SYNC_BATCH=10
TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS=300
TRUDVSEM_VACANCY_TTL_DAYS=45
TRUDVSEM_CLOSED_RETENTION_DAYS=30
TRUDVSEM_RETRY_BASE_SECONDS=60
TRUDVSEM_RETRY_MAX_SECONDS=3600
```

После изменения Environment использовать `Save, rebuild and deploy`.

## 4. Health после deploy

Открыть:

```text
/health/live
/health/ready
```

Ожидается:

```text
status=ok
database.backend=postgresql
database.persistent=true
current_revision=20260807_0004
expected_revision=20260807_0004
```

## 5. Diagnostics checkpoint

Временно включить только для проверки:

```text
DEBUG_DIAGNOSTICS=1
DIAGNOSTICS_SECRET=<random secret>
```

Вызвать `/trudvsem/status` с `X-Diagnostics-Secret`.

Зафиксировать до run:

```text
checkpoint.watermark_at
checkpoint.pending
checkpoint.pending_offset
checkpoint.next_retry_at
active_total
closed_total
cached_total
```

## 6. Запуск incremental sync

Через защищённый endpoint:

```http
POST /sync/trudvsem
X-Sync-Secret: <SYNC_SECRET>
```

Ожидается HTTP `202` и один queued run.

Во время работы checkpoint должен содержать bounded window. Public endpoint `/api/sources/trudvsem/status` остаётся sanitised и показывает только running/queued/progress/cache.

## 7. Проверка continuation

Если provider total превышает items на один run:

- terminal SyncRun details первого chunk: `window_complete=false`;
- checkpoint `pending=true`, `pending_offset>1`;
- следующий worker cycle продолжает offset;
- после complete window `pending=false`, watermark продвигается.

Нельзя вручную изменять checkpoint в production.

## 8. Проверка дублей

Сравнить count source rows до и после overlap/retry. Повторный incremental run с теми же IDs не должен увеличивать число `(source, external_id)`.

Наличие overlap само по себе ожидаемо и не является дублем.

## 9. Проверка failure preservation

Безопасный вариант — временно использовать тестовый/локальный mock. В production не ломать endpoint намеренно без окна наблюдения.

Ожидается:

```text
run.status=failed
watermark unchanged
pending cursor preserved
next_retry_at set
cached_total unchanged
worker remains alive
```

## 10. Проверка cleanup

Production cleanup выполняется только после complete successful window.

Проверка на тестовой БД:

1. создать active row с `published_at` старше TTL;
2. создать closed row с `closed_at` старше retention;
3. завершить successful window;
4. проверить: первая запись closed/hidden, вторая purged;
5. повторно upsert active payload — запись реактивируется.

Не уменьшать TTL в production только ради теста.

## 11. Restart persistence

1. Зафиксировать checkpoint и `cached_total`.
2. Выполнить `Restart service`.
3. После `Live` проверить revision 0004.
4. Убедиться, что watermark/cache сохранились.
5. Если был pending window — worker должен продолжить его или безопасно восстановить stale run.

## 12. Завершение диагностики

После теста:

- `DEBUG_DIAGNOSTICS=0`;
- удалить `DIAGNOSTICS_SECRET`;
- выполнить deploy;
- убедиться, что `/trudvsem/status` снова `404` без доступа.

## 13. Rollback

### Application rollback без schema downgrade

1. `TRUDVSEM_SYNC_ENABLED=0`.
2. Остановить worker/redeploy предыдущий commit.
3. Revision `0004` можно оставить: она additive.
4. Cache не удалять.

### Schema downgrade

Только после verified backup и остановленного worker:

```text
alembic downgrade 20260807_0003
```

Downgrade удалит checkpoint и lifecycle columns; continuation/retry state будет потерян. Поэтому application-only rollback предпочтителен.

## 14. Итоговый протокол

```text
GitHub CI: <green/red>
Render revision: <...>
Checkpoint before/after: <...>
Continuation: <passed/not exercised>
Retry/cache preservation: <passed/not exercised>
Cleanup/lifecycle: <passed/not exercised>
Restart persistence: <passed/not exercised>
Final status: <НУЖНА ПРОВЕРКА/ВЫПОЛНЕНО>
```

# AI Career Agent — реализация SEARCH-005

| Поле | Значение |
|---|---|
| Документ | SEARCH005_IMPLEMENTATION |
| Пакет | SEARCH-005 |
| Версия | 1.0 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | GitHub main после PRIV-001 COMPLETE |
| Production revision | `20260813_0013` |
| Candidate revision | `20260819_0014` |

## 1. Цель и границы

SEARCH-005 создаёт безопасный read-only центр состояния источников вакансий для ограниченного администратора. Он не является credential manager, public status page или механизмом ручного запуска upstream-запросов.

## 2. Admin authorization

Доступ разрешён только при одновременном выполнении:

```text
verified first-party User
+ active server-side AuthSession
+ normalized email in SEARCH_ADMIN_EMAILS
```

Обычному авторизованному пользователю возвращается neutral 404. Пустой allowlist отключает admin center целиком. Диагностический секрет и OAuth identity не дают admin-доступ.

## 3. Persistent state

`SourceHealthState` хранит текущий безопасный агрегат по каждому provider:

```text
provider
availability
configured
last_attempt_at / last_success_at / last_failure_at
last_latency_ms
consecutive_failures
error_category / error_code
cache_observed_at / cache_item_count
details_json (strict allowlist)
created_at / updated_at
```

Отсутствуют `user_id`, токены, response body, query, URL, external identity и PII.

## 4. Observation pipeline

Существующая `OPS_STATE` provider telemetry получает non-gating instrumentation adapter. Adapter связывает только provider/source, success/status, bounded latency and exception class. DB failure не меняет результат поиска. Exception message не сохраняется.

Trudvsem дополнительно агрегирует persistent `sync_runs`, `sync_workers` и cache/checkpoint metadata. Страница не выполняет внешний network probe.

## 5. UI and API

- `GET /admin/sources` — responsive HTML;
- `GET /api/admin/sources` — safe JSON;
- no-store, no ETag, rate limit;
- status: available/cached/degraded/auth_required/temporarily_unavailable/disabled/unknown;
- timestamps, latency, failure streak, cache count and safe Trudvsem worker/run fields.

## 6. Code impact

```text
domain/source_health.py
models/source_health.py
repositories/source_health.py
services/source_health.py
services/source_health_instrumentation.py
services/admin_access.py
routes/admin_sources.py
templates/admin/source_center.html
migrations/versions/20260819_0014_source_health_admin.py
```

Updated: `app.py`, `database.py`, config helpers, model registration, backup inventory, base navigation, CSS, env examples, CI, tests and repository documentation.

## 7. Migration

Revision `20260819_0014` creates `source_health_states`, constraints and indexes. Existing user/search/profile/privacy data is unchanged. Downgrade drops only this table.

## 8. Local verification

Full available tests, focused SEARCH-005 tests, compile/AST, migration round-trip, repository hygiene, infra manifest and archive checks passed. PostgreSQL/Render/admin E2E remains external.

## 9. Risks and limitations

- allowlist is deliberate deployment-level authorization, not full RBAC;
- future multiple web replicas require shared event transport for complete cross-process telemetry;
- metadata cache probing is fail-soft;
- no admin actions in candidate;
- provider status is operational evidence, not SLA guarantee.

## 10. Rollback

Application revert may keep additive 0014. Remove `SEARCH_ADMIN_EMAILS` to disable access immediately. Controlled downgrade removes only source health state.

## 11. Next action

Green Pull Request CI, configure admin allowlist, Render 0014, admin/non-admin/provider/restart/log production E2E.

## 12. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 19.08.2026 | Implemented explicit admin boundary, persistent source health, safe UI/API, instrumentation, migration, tests and rollback contract. |

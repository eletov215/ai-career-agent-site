# AI Career Agent — source health contract reference SEARCH-005

| Поле | Значение |
|---|---|
| Документ | SEARCH005_SOURCE_HEALTH_REFERENCE |
| Пакет | SEARCH-005 |
| Версия | 1.0 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Providers

Canonical provider keys: `hh`, `superjob`, `reed`, `trudvsem`.

## 2. Availability

```text
unknown
available
cached
degraded
auth_required
temporarily_unavailable
disabled
```

`available` is based on latest successful operational observation, not a contractual SLA. `cached` indicates usable cache with stale/absent live observation. `disabled` is deployment configuration.

## 3. Persistent fields

| Field | Contract |
|---|---|
| provider | canonical provider key, PK |
| availability | enum above |
| configured | boolean only, never credential value |
| last_attempt/success/failure | UTC timestamps |
| last_latency_ms | bounded 0..3,600,000 |
| consecutive_failures | bounded non-negative counter |
| error_category | safe category |
| error_code | exception class or safe status token, max 64 |
| cache_observed_at/count | metadata only |
| details_json | strict allowlist of bounded scalars |

## 4. Allowed details

`reported_total`, `known_total`, `snapshot_count`, `active_run`, `worker_alive`, `worker_age_seconds`, `last_run_status`, `checkpoint_offset`, `checkpoint_total`, `configured_reason`.

## 5. Forbidden data

Credentials, tokens, response bodies, stack traces, arbitrary exception messages, user queries, URLs with query/fragment, user/email/external identity IDs, resume/profile content.

## 6. Update semantics

Success resets failure streak and clears safe error fields. Failure increments streak and records only category/code. Unknown provider keys are rejected. Telemetry write failure is non-gating. Admin refresh may update configuration/cache/sync metadata without external I/O.

## 7. Persistence and restart

Current state survives database-backed restart. No unbounded event history is created. Future multi-replica operation requires shared event transport to guarantee complete observations from every process.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 19.08.2026 | Provider keys, states, safe fields, update semantics and privacy boundaries defined. |

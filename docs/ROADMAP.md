# AI Career Agent — ROADMAP




<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты — 2026-08-24

- `SEARCH-005` — **ВЫПОЛНЕНО**.
- `AI-BENCH-001 implementation` — **КАНДИДАТ ГОТОВ**.
- `AI-BENCH-001 live comparative run + manual rubric` — **НУЖЕН ВНЕШНИЙ ПРОГОН**.
- `AI-PROVIDER-001` — **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ BENCHMARK**.
- Production schema remains `20260819_0014`; production routes and migrations were not changed.
<!-- ACA-CANONICAL-STATUS:END -->

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001/002/003 | ВЫПОЛНЕНО | regression only |
| PRIV-001 | ВЫПОЛНЕНО | Green CI + Render `0013` + export/delete/restart/log E2E confirmed |
| SEARCH-005 | НУЖНА ПРОВЕРКА | next package; admin source-health center |
| AI-BENCH/AI-PROVIDER/LEGAL/AI-* | ЗАПЛАНИРОВАНО | later MVP stages |
| INFRA-001 | ОТЛОЖЕНО | pre-release window |

## Current flow

```text
PROF-001 complete
-> PROF-002 complete
-> PROF-003 complete
-> PRIV-001 complete
-> SEARCH-005 ready
```

## PROF-003 completed scope

Server drafts/autosave, immutable versions/history/restore, durable photo/logo assets, preview/PDF export parity, owner isolation, stale protection, cross-device/restart persistence and final regression/log review are confirmed on production revision `20260812_0012`.

## PRIV-001 — ВЫПОЛНЕНО

Production `0013` confirmed. Owner-readable re-authenticated ZIP export, current-password + exact-phrase account deletion, local HH/SuperJob credential cleanup, identifier-free privacy audit, technical retention worker, asset retention and restart/log regression passed. Legal policy wording/final retention and remote provider grant revoke remain outside the package claim.

Next: `SEARCH-005` — НУЖНА ПРОВЕРКА.

## SEARCH-005 — ВЫПОЛНЕНО

Цель: защищённый admin center для availability/latency/freshness/import state источников на базе уже существующих OPS/SYNC/search telemetry. Public/user surface остаётся кратким и sanitised; admin details не содержат tokens/credentials/PII. Dependencies AUTH-001, OPS-001, SYNC-001 выполнены.

## SEARCH-005 candidate
Status: NEEDS VERIFICATION. Read-only admin source center, persistent health state and migration 0014. Next after completion: AI-BENCH-001.

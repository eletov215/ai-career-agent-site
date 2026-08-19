# AI Career Agent — ROADMAP

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001/002/003 | ВЫПОЛНЕНО | regression only |
| PRIV-001 | НУЖНА ПРОВЕРКА | PR CI -> Render `0013` -> destructive throwaway E2E |
| SEARCH-005 | ЗАПЛАНИРОВАНО | after PRIV-001 complete |
| AI-BENCH/AI-PROVIDER/LEGAL/AI-* | ЗАПЛАНИРОВАНО | later MVP stages |
| INFRA-001 | ОТЛОЖЕНО | pre-release window |

## Current flow

```text
PROF-001 complete
-> PROF-002 complete
-> PROF-003 complete
-> PRIV-001 export/delete/retention candidate
-> SEARCH-005
```

## PROF-003 completed scope

Server drafts/autosave, immutable versions/history/restore, durable photo/logo assets, preview/PDF export parity, owner isolation, stale protection, cross-device/restart persistence and final regression/log review are confirmed on production revision `20260812_0012`.

## PRIV-001 — НУЖНА ПРОВЕРКА

Candidate adds owner-readable ZIP export, current-password + exact-phrase account deletion, local HH/SuperJob credential cleanup, identifier-free privacy audit, technical retention cleanup worker and migration `20260813_0013`. Legal policy wording/retention finalization and remote provider grant revoke are explicitly outside the candidate claim.

Next after completion: `SEARCH-005`.

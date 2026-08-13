# AI Career Agent — ROADMAP

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001 | ВЫПОЛНЕНО | regression only |
| PROF-002 | ВЫПОЛНЕНО | regression only |
| PROF-003 | ГОТОВО К СТАРТУ | server drafts/versions package |
| PRIV-001 | ЗАПЛАНИРОВАНО | profile/import foundation required |
| SEARCH-005 | ЗАПЛАНИРОВАНО | after account/profile/privacy foundation |
| AI-BENCH/AI-PROVIDER/LEGAL/AI-* | ЗАПЛАНИРОВАНО | later MVP stages |
| INFRA-001 | ОТЛОЖЕНО | pre-release window |

## Current flow

```text
PROF-001 complete
-> PROF-002 complete
-> PROF-003 drafts/versions
-> PRIV-001 export/delete/retention
```

## PROF-002 completed scope

- authenticated bounded text-PDF upload;
- deterministic structured suggestions;
- confidence, warnings, conflicts and evidence;
- preserve existing confirmed scalar values by default;
- editable full-profile review;
- no persistence before explicit confirm;
- owner/version-bound timed metadata token;
- immutable history source + aggregate provenance;
- invalid/image-only/oversized/foreign/expired/stale/CSRF negative controls;
- migration/tests/CI/docs.

Excluded: OCR, DOC/DOCX, LLM/AI parser, provider resume import, background jobs, persisted review drafts/autosave, auto-confirm and historical restore.

## PROF-003 — НУЖНА ПРОВЕРКА (candidate 13.08.2026)

Server-side resume drafts, optimistic autosave, immutable checkpoint/export/restore versions, durable images, history/restore and migration `20260812_0012` implemented. External Pull Request CI, Render `0012` and production owner/persistence/export/mobile/regression gate remain.

Next after completion: `PRIV-001`.

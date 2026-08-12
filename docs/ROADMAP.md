# AI Career Agent — ROADMAP

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001 | НУЖНА ПРОВЕРКА | PR CI, Render 0010, owner/version/restart E2E |
| PROF-002 | ЗАПЛАНИРОВАНО | starts after PROF-001 complete |
| PROF-003 / PRIV-001 | ЗАПЛАНИРОВАНО | profile foundation required |
| SEARCH-005 | ЗАПЛАНИРОВАНО | after account/profile/privacy foundation |
| AI-BENCH/AI-PROVIDER/LEGAL/AI-* | ЗАПЛАНИРОВАНО | later MVP stages |
| INFRA-001 | ОТЛОЖЕНО | pre-release window |

## Current flow

```text
PROF-001 candidate
-> branch / PR
-> CI green
-> Render 20260811_0010
-> owner/version/concurrency/restart E2E
-> PROF-001 complete
-> PROF-002 import + editable review
-> PROF-003 drafts/versions
-> PRIV-001 export/delete/retention
```

## PROF-001 scope

- owner-scoped current profile;
- immutable material-change versions;
- partial profile allowed;
- manual confirmation only;
- bounded validation and optimistic conflict;
- `/profile` view/edit/history;
- backup/migration/tests/CI.

Excluded: resume import, AI facts, autosave, version restore, public profile and privacy lifecycle controls.

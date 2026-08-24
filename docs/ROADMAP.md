# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты — 2026-08-24

- `SEARCH-005` — **ВЫПОЛНЕНО**.
- `AI-BENCH-001 candidate v1.4.32` — **ОТКЛОНЁН CI** из-за false positive numeric scanner.
- `AI-BENCH-001 hotfix r1 / evals 1.0.1` — **НУЖНА ПРОВЕРКА GITHUB ACTIONS**.
- После green CI: live comparative run + manual rubric.
- `AI-PROVIDER-001` — **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 hotfix r1
-> GitHub package gate + full Python tests
-> approved live model candidates and exact model IDs
-> comparative run on one dataset fingerprint
-> manual quality rubric
-> AI-PROVIDER-001
-> LEGAL-001
-> AI-001..006
-> JOB-001..004
```

## Статусы

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..005 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001/002/003, PRIV-001 | ВЫПОЛНЕНО | regression only |
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | repeat GitHub CI, then live comparison/manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

Hotfix r1 repairs benchmark infrastructure only. It does not select an external model, connect production AI, change the database or expose new user routes.

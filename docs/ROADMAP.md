# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-09-13

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- Alice Final run #5 artifact `33168005097` / run `ai-bench-20260828T114615Z-5b0d7a99` - **8/8 MACHINE PASS** under grounded-v2.5, with 0 errors/retries and quality/grounding 1.000.
- Named human reviewer **Шекунов Д.С.** marked AI-BENCH writing **REVISION REQUIRED** for cases 1, 3, 5 and 6.
- `AI-BENCH-001 grounded-v2.6 / evals 1.6.0` - **НУЖНА ПРОВЕРКА**: softer RU coaching, actionable vacancy-gap guidance, first-person cover letters, internal-only caveats, hard presentation gate.
- Retained run #5 raw replay under grounded-v2.6 is **6/8**, deliberately rejecting both old cover letters.
- Next: green ordinary CI/package gate -> fresh Alice Final 8/8 -> focused named human re-review -> AI-BENCH-001 closure decision.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 grounded-v2.6 / evals 1.6.0
-> green ordinary CI/package gate
-> fresh Alice Final 8/8
-> focused named human re-review (1, 3, 5, 6)
-> AI-BENCH-001 closure decision
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | grounded-v2.6 ordinary CI -> fresh Alice Final 8/8 -> focused named human re-review |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
- `AI-BENCH-001 grounded-v2.6 / evals 1.6.0` - **НУЖНА ПРОВЕРКА**: human-writing corrections implemented; ordinary CI, fresh Alice Final live verification and focused named human re-review remain.

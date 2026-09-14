# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-09-14

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- Alice Final run #6 artifact `34766480932` / run `ai-bench-20260913T154901Z-44d67112` - 8/8 calls, 0 errors/retries, **7/8 MACHINE** under grounded-v2.6.
- Единственный FAIL: `cover-letter-en-01` с 3 unsupported impact claims; дополнительно выявлено неподтвержденное `long admired...` в motivation.
- `AI-BENCH-001 grounded-v2.6.1 / evals 1.6.1` - **НУЖНА ПРОВЕРКА**: atomic EN candidate-fit prompt, unsupported employer-familiarity gate, run #6 regressions; hard thresholds unchanged.
- Next: green ordinary CI/package gate -> fresh Alice Final 8/8 -> focused named human re-review -> AI-BENCH-001 closure decision.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Render staging web uses Neon PostgreSQL (Oregon); `/health/ready` confirmed revision/migrations `20260819_0014` and healthy persistent database.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 grounded-v2.6.1 / evals 1.6.1
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | grounded-v2.6.1 ordinary CI -> fresh Alice Final 8/8 -> focused named human re-review |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
- `AI-BENCH-001 grounded-v2.6.1 / evals 1.6.1` - **НУЖНА ПРОВЕРКА**: Alice run #6 impact-extension regressions and atomic EN cover-letter hardening implemented; ordinary CI, fresh Alice Final live verification and focused named human re-review remain.

# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-08-27

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- comparative grounded-v2.2 live run #4 - **REVIEWED**; Alice AI LLM nominated as primary candidate.
- Alice Final run #1 artifact `33061758538` - **TRANSPORT PASS / MACHINE 6/8**: 8/8 calls, 0 errors/retries; оба FAIL локализованы в interview structured scenario provenance, RU также содержит numeric false positive `2-3 примера`.
- `AI-BENCH-001 Alice Final v2 / evals 1.5.0 / grounded-v2.3` - **НУЖНА ПРОВЕРКА**.
- Offline replay retained raw responses -> **8/8**, six audited unique scenario-provenance repairs, zero unresolved provenance/unsupported numbers; replay is not a new provider result.
- Next: green ordinary CI -> fresh Alice-only final run -> 8/8 machine gate -> artifact raw/machine/presentation audit -> named human writing rubric.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 grounded-v2.3 Alice Final v2 -> green ordinary CI
-> CI workflow_dispatch(run_ai_bench_alice_final=true)
-> fresh Alice AI LLM benchmark 1.4 / dataset 1.3.2
-> 8/8 machine-safety artifact with zero unresolved safety violations
-> raw/machine/presentation artifact audit
-> named manual writing-quality rubric
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | green CI -> fresh Alice-only 8/8 machine gate -> artifact audit -> named manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
- `AI-BENCH-001 Alice Final v3 / evals 1.5.1 / grounded-v2.4` - **НУЖНА ПРОВЕРКА**: fresh Alice-only 8/8 machine gate, then named human rubric.

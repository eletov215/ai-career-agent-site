# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-08-27

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- grounded-v2.2 comparative live run #4 - **TRANSPORT PASS / SAFETY REVIEWED**: 24/24 calls, 0 errors/retries; Alice 5/8, Flash 5/8, YandexGPT Pro 4/8.
- Alice AI LLM - **PRIMARY CANDIDATE**, но ещё не production provider.
- `AI-BENCH-001 Alice final / evals 1.4.1` - **НУЖНА ПРОВЕРКА**.
- Next: green ordinary CI -> manual Alice-only final run -> 8/8 machine gate -> named human writing rubric.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 grounded-v2.2 Alice-final -> green ordinary CI
-> CI workflow_dispatch(run_ai_bench_alice_final=true)
-> Alice AI LLM 8/8 machine-safety artifact
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | green CI -> Alice-only 8/8 machine gate -> named manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.

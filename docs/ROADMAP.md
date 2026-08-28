# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-08-28

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- comparative Yandex benchmark completed; Alice AI LLM remains the primary final candidate.
- Alice Final run #4 artifact `33165683757` / run `ai-bench-20260828T111023Z-62a5cc1a` - **8/8 MACHINE PASS**: 8/8 calls, 0 errors/retries, zero hard-safety counters.
- Artifact audit found one deterministic presentation-sanitizer gap: grouped known markers `(c1, c2)` / `(v1, v2)` survived in two `interview-en-01` purpose strings although `purpose` is user-facing.
- `AI-BENCH-001 artifact-sanitization hotfix r1 / evals 1.5.3 / grounded-v2.5` - **НУЖНА ПРОВЕРКА**; prompts/provider inputs and production code unchanged.
- Retained live raw responses replay **8/8** with 3 audited scenario repairs, 20 audited marker removals and **0 residual evidence IDs** in declared user-facing paths.
- Next: green ordinary CI/package gate -> named human writing-quality rubric -> AI-BENCH-001 closure decision.
- A second billable Alice call is not required for this sanitizer-only correction because the successful live raw evidence and machine semantics are unchanged.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 live Alice 8/8 machine gate COMPLETE
-> artifact-sanitization hotfix r1 / evals 1.5.3
-> green ordinary CI/package gate
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | live 8/8 complete; sanitizer hotfix ordinary CI -> named manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
- `AI-BENCH-001 artifact-sanitization hotfix r1 / evals 1.5.3 / grounded-v2.5` - **НУЖНА ПРОВЕРКА**: live 8/8 machine gate complete; ordinary CI for deterministic sanitizer, then named human rubric.

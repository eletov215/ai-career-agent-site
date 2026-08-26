# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.6 |
| Дата | 26 августа 2026 |
| Пакет | AI-BENCH-001 grounded-v2 hardening |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #2 + MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. Closed stability gate and first live transport

Stability r4 is externally confirmed: ordinary CI on `main` passed `Python tests` and the dedicated AI-BENCH package gate. The live job correctly skipped on push. Manual run then completed successfully and produced artifact `32958938365`.

All three providers completed 8/8 API calls with `error_count=0`. Therefore this run confirms benchmark transport/configuration, not model fitness.

## 2. First live machine evidence

| Provider | Passed | Quality | Grounding | p50 ms | p95 ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| Alice AI LLM | 4/8 | 0.952178 | 0.957259 | 5193.153 | 9444.269 | 0.047868023 |
| Alice AI LLM Flash | 2/8 | 0.950094 | 0.897536 | 3146.667 | 3919.065 | 0.006081147 |
| YandexGPT Pro 5.1 | 3/8 | 0.937723 | 0.859077 | 5738.538 | 7977.200 | 0.034518028 |

These grounded-v1 scores are historical and must not be compared numerically to grounded-v2 scores as if the scoring contract were unchanged.

## 3. Why AI-BENCH-001 is not complete

Artifact review found real model failures (unsupported skills/impact, malformed evidence, weak match consistency) and benchmark weaknesses (user-facing evidence leakage, model-authored numeric match score, false-positive hypothetical-number handling). Selecting a provider now would freeze known safety/quality defects into the production design.

## 4. Grounded-v2 verification target

Evals 1.2.0 must prove:

- exact raw evidence IDs and no internal evidence metadata in user-facing text;
- structured `facts_not_verified` and cover-letter `caveats` with required evidence coverage;
- candidate-fit claims supported by candidate facts;
- unsupported impact claims blocked;
- each vacancy requirement classified exactly once with mandatory evidence;
- deterministic numeric match score derived by code, not authored by LLM;
- hypothetical interview numbers allowed only when supplied as scenario facts;
- live-run #1 failure patterns covered by regression tests;
- separate pending manual writing-review template.

## 5. Local candidate evidence

- deterministic grounded-v2 reference run: 8/8 PASS under strict gates;
- AI-BENCH unit/package regression suite covers the new contracts and known first-run failure patterns;
- benchmark package checker verifies version/schema/dataset/workflow invariants;
- production revision/routes/dependencies remain unchanged.

Full repository CI remains authoritative for environment-dependent PostgreSQL/Docker and historical package checks.

## 6. Remaining external gate

1. Green ordinary GitHub CI for this grounded-v2 candidate.
2. Manual `CI` run with `run_ai_bench_live=true` on `main`.
3. Review sanitized live run #2 artifact.
4. Complete named human writing-quality rubric.
5. Record final benchmark decision; only then unblock `AI-PROVIDER-001`.

## 7. Status decision

`AI-BENCH-001` remains **НУЖНА ПРОВЕРКА**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.  
No production AI provider is connected.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.5 | 26.08.2026 | Stability r4 fixed invalid job-level `runner` context. |
| 1.6 | 26.08.2026 | Green CI + first live run reviewed; grounded-v2 hardening defines second-run gate before provider selection. |

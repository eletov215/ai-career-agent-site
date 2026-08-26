# AI Career Agent - аудит источников v1.4.38

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.38 |
| Дата | 26 августа 2026 |
| Проверяемый пакет | AI-BENCH-001 grounded-v2 hardening |
| Исходный код | `ai-career-agent-site-main (22).zip`, предоставленный как актуальный GitHub `main` |
| Live evidence | artifact `ai-bench-001-yandex-live-32958938365.zip` |
| Production revision | `20260819_0014` |
| Результат | first live run transport подтверждён; hardening candidate подготовлен; нужен GitHub CI + live run #2 |

## 1. Подтверждённое состояние перед hardening

После stability r4 пользователь подтвердил green CI на `main`: `Python tests` и `AI-BENCH-001 package gate` прошли, live job корректно skipped на push. Затем manual `workflow_dispatch` завершился Success и выполнил comparative Yandex run.

Artifact содержит 24 response files (8 cases x 3 providers), `run.json` and `report.md`. For every provider `error_count=0`, therefore API key, Folder ID, service-account permission, model routing, JSON structured-output transport and artifact upload worked for this run.

| Provider | Strict pass | Quality | Grounding | p50 ms | p95 ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| Alice AI LLM | 4/8 | 0.952178 | 0.957259 | 5193.153 | 9444.269 | 0.047868023 |
| Alice AI LLM Flash | 2/8 | 0.950094 | 0.897536 | 3146.667 | 3919.065 | 0.006081147 |
| YandexGPT Pro 5.1 | 3/8 | 0.937723 | 0.859077 | 5738.538 | 7977.200 | 0.034518028 |

`Machine status: failed` represents quality-gate evidence, not transport failure. No provider decision is made from this run.

## 2. Live run #1 findings driving grounded-v2

- Alice AI LLM had the strongest overall grounding but still introduced an unsupported Kubernetes recommendation, returned incomplete `facts_not_verified`, emitted an invalid evidence ID in RU vacancy match, and produced unsupported causal/impact language in a cover letter.
- Alice AI LLM Flash was much cheaper/faster but unstable on vacancy-match classification and could understate required gaps.
- YandexGPT Pro 5.1 produced inconsistent model-authored match scores and malformed/decorated evidence IDs in some cases.
- The old benchmark also produced false positives for legitimate hypothetical interview numbers because it could not distinguish scenario numbers from invented candidate achievements.
- User-facing text could pass while leaking internal evidence metadata, so claim/evidence metadata needed a stronger separation from presentation text.

## 3. Grounded-v2 implementation

`evals/VERSION` is `1.2.0`; benchmark contract is `1.1`; dataset manifest is `1.1.0` with `contract=grounded-v2`.

Implemented controls:

- source facts are typed `candidate` / `vacancy` / `scenario`;
- evidence IDs must match raw `^[a-z][0-9]+$` identifiers;
- user-facing strings reject technical evidence labels and decorated known IDs;
- resume `facts_not_verified` and cover-letter `caveats` are structured with evidence IDs;
- cover-letter `candidate_fit` paragraphs require candidate evidence;
- unsupported impact/causal claims are a hard gate unless supported by cited candidate evidence;
- vacancy-match output no longer contains model-authored `match_score`;
- every vacancy requirement is classified exactly once as matched/gap and checked against expected status/evidence;
- deterministic weighted code derives the numeric match score and verdict check;
- interview hypothetical numbers are accepted only when supplied as source/scenario facts;
- live-run #1 failure patterns are encoded in `evals/regressions/live-run-1.json`;
- runner emits `manual_review_template.json`; manual writing review cannot override machine safety gates;
- report/run fingerprints remain visible while credential-bearing fields continue to be redacted.

## 4. Regression and deterministic evidence

The grounded-v2 deterministic reference run passes all 8 reference cases with strict thresholds. Current local package tests cover invalid/decorated evidence IDs, metadata leakage, unsupported impact, structured verification/caveats, duplicate/wrong/missing match classifications, candidate/vacancy evidence requirements, deterministic scores and scenario-number policy.

Repository evidence under `docs/evidence/ai-bench-001/` is regenerated for contract 1.1, including a separate pending manual-review template. Live run #1 is summarized without copying credentials or production user data.

## 5. Production boundary

No production Flask route, model, repository, service, dependency, Render setting or Alembic migration is changed by grounded-v2. Production revision remains `20260819_0014`. GitHub Secrets remain external to repository content and live requests remain manual-only/default-off.

## 6. Current gate

1. Upload grounded-v2 candidate from the current `main` base.
2. Require green ordinary `Python tests` and `AI-BENCH-001 package gate`, including historical package checks.
3. Run `Actions -> CI -> Run workflow -> run_ai_bench_live=true` on `main`.
4. Download live run #2 artifact and compare machine evidence against run #1 qualitatively (scores are not directly comparable because contract changed).
5. Complete named human writing-quality rubric.
6. Only then decide whether AI-BENCH-001 can be closed and unblock AI-PROVIDER-001.

## 7. Status decision

`AI-BENCH-001 grounded-v2 hardening` - **НУЖНА ПРОВЕРКА**.  
Previously completed packages remain **ВЫПОЛНЕНО**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАНО**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.37 | 26.08.2026 | Stability r4 removed invalid job-level `runner` context. |
| 1.4.38 | 26.08.2026 | Ordinary CI green and live run #1 reviewed; grounded-v2 evidence/safety/match hardening prepared for live run #2. |

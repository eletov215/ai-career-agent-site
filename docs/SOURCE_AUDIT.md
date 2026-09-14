# AI Career Agent - аудит источников v1.4.47

**Дата:** 14.09.2026  
**Production revision:** `20260819_0014`

| Поле | Значение |
|---|---|
| Проверяемая кодовая основа | GitHub `main` after grounded-v2.6 commit `b1d54b5`; current delta is grounded-v2.6.1 prepared from that state |
| SHA-256 исходного ZIP | `a8f4d00d747dd20b5cc4b9fc6e49f9ec00148607445add447751592f347210a1` |
| Проверяемый пакет | AI-BENCH-001 grounded-v2.6.1 atomic EN cover-letter hardening |
| Evals | `1.6.1` |
| Benchmark contract | `1.4` |
| Dataset | `ai-career-agent-golden-v1` v`1.3.6`, `contract=grounded-v2.6.1` |
| External evidence | Alice Final run #6 artifact `34766480932`; run ID `ai-bench-20260913T154901Z-44d67112`; prior named human reviewer Шекунов Д.С. |
| Результат | run #6 transport 8/8 / machine 7/8; only EN cover-letter impact FAIL; grounded-v2.6.1 candidate needs ordinary CI -> fresh Alice Final 8/8 -> focused human re-review |

## 1. Source precedence

Пользователь предоставил `ai-career-agent-site-main (1).zip` 13.09.2026 как актуальный snapshot GitHub `main`. Для этой поставки он имеет приоритет над предыдущими архивами. SHA-256 исходного ZIP: `a8f4d00d747dd20b5cc4b9fc6e49f9ec00148607445add447751592f347210a1`. Sanitized Alice artifacts используются только как external benchmark evidence; secret values и production user data в репозиторий не копируются.

Последнее внешнее evidence — artifact `34766480932`, run `ai-bench-20260913T154901Z-44d67112`, выполненный на GitHub `main` с grounded-v2.6. Transport чистый: 8/8 calls, 0 errors/retries. Machine gate = **7/8**; единственный FAIL — `cover-letter-en-01` with 3 unsupported inferred impact claims. Поэтому текущий delta — `grounded-v2.6.1` atomic EN cover-letter hardening, а не provider selection.


## 2. Prior run #5 + named human audit

Artifact `ai-bench-001-yandex-alice-final-33168005097.zip` / run `ai-bench-20260828T114615Z-5b0d7a99` completed 8/8 provider calls with 0 errors, 0 retries and **8/8 machine PASS**. Mean quality and grounding were `1.000`; p50 `3447.243 ms`, p95 `5500.041 ms`, estimated cost `USD 0.0504295`; all machine hard counters were zero.

Named reviewer **Шекунов Д.С.** then required revisions in four areas: softer RU resume recommendations; actionable RU vacancy-match guidance; and RU/EN cover letters that read as first-person human applications without advertising unverified gaps. Cases 2, 4, 7 and 8 were accepted. Exact review evidence is `docs/evidence/ai-bench-001/alice-final-run-5-human-review.md`; numeric scores are recorded only where the reviewer explicitly supplied them.

Grounded-v2.6.1 / evals 1.6.1 applies only to the benchmark layer:

- dataset `1.3.6`, contract `grounded-v2.6.1`;
- softer conditional RU coaching prompt;
- vacancy recommendation prompt explains `confirm/update -> deterministic recalculation` and forbids invented future percentages;
- cover-letter caveats remain required internal audit metadata but are excluded from `presentation/`;
- visible cover letters hard-fail explicit unverified candidate-gap evidence/disclosure, third-person writer labels, or missing first-person voice;
- gap-bearing paragraphs are no longer auto-repaired into visible motivation;
- production routes/services/models/migrations and revision `20260819_0014` are unchanged.

Retained run #5 raw responses replay under grounded-v2.6 is **6/8**: both historical cover-letter outputs are now intentionally rejected. Evidence: `docs/evidence/ai-bench-001/alice-final-run-5-grounded-v2.6-replay.json`. Because the prompts changed, replay cannot close the package; a fresh Alice Final live run is mandatory after ordinary CI.

## 3. Alice Final run #4 audit

Artifact `ai-bench-001-yandex-alice-final-33165683757.zip` / run `ai-bench-20260828T111023Z-62a5cc1a` содержит 8 raw responses, 8 machine responses, 8 presentation responses, `run.json`, `report.md` и pending manual-review template.

| Метрика | Значение |
|---|---:|
| API calls | 8/8 |
| Provider errors | 0 |
| Retries | 0 |
| Machine pass | **8/8** |
| Mean quality | 0.999479 |
| Mean grounding | 0.994792 |
| Language consistency | 1.000 |
| Match consistency | 1.000 |
| p50 | 3734.228 ms |
| p95 | 8872.01 ms |
| Estimated cost | USD 0.052416386 |

Все hard-safety counters равны нулю. Live machine gate закрыт.

Raw/machine/presentation audit выявил один deterministic presentation defect: в `interview-en-01` два user-facing `purpose` содержали grouped known evidence markers `(c1, c2)` / `(v1, v2)` и `(c1, c2, v2)`. Grounded-v2.5 sanitizer удалил 13 одиночных markers, но не умел очищать несколько known IDs внутри одной пары скобок. Так как `purpose` входит в declared user-facing paths, manual rubric нельзя начинать на таком presentation artifact.

Artifact-sanitization hotfix r1 расширяет только presentation cleanup: полностью known-ID groups через comma/semicolon удаляются и каждый ID аудируется; mixed/unknown groups остаются нетронутыми и hard-fail metadata gate. Retained raw responses replay 8/8, scenario repairs 3, marker cleanups 20, residual user-facing evidence IDs 0. Evidence: `docs/evidence/ai-bench-001/alice-final-run-4-presentation-replay.json`.

Local bounded repository verification после hotfix: **358 passed, 14 environment-dependent skipped, 19 subtests passed**; AI-BENCH package gate PASS; repository hygiene PASS.

Повторный billable Alice call не требуется: prompts, provider input/output, raw responses, machine safety semantics и thresholds не меняются. Следующий gate - ordinary GitHub CI/package gate для sanitizer hotfix, затем named human writing-quality rubric.

## 4. Alice Final run #3 audit

Artifact `ai-bench-001-yandex-alice-final-33163009779.zip` / run `ai-bench-20260828T102540Z-bcf4c2ed` содержит 8 raw responses, 8 machine responses, 8 presentation responses, `run.json`, `report.md` и pending manual-review template.

| Метрика | Значение |
|---|---:|
| API calls | 8/8 |
| Provider errors | 0 |
| Retries | 0 |
| Source machine pass | 6/8 |
| Mean quality | 0.975 |
| Mean grounding | 1.000 |
| p50 | 4796.74 ms |
| p95 | 11855.16 ms |
| Estimated cost | USD 0.051498352 |

Confirmed failures:

- `cover-letter-en-01`: no schema/evidence/language failure; an explicit unverified experimentation gap (`c5`) plus vacancy preference (`v3`) was followed by future-learning intent but labeled `candidate_fit`. The phrase `grow in this area` was therefore classified as unsupported `growth_increase`. This is a paragraph-kind/intent mismatch, not an invented candidate achievement.
- `interview-ru-01`: no provenance/language/schema failure remained; only `2–3` in `Назовите 2–3 ресурса или подхода...` was treated as unsupported factual number. It is answer cardinality, not duration/experience/percentage/achievement.

### Grounded-v2.5 implementation audit

- motivation normalization now allows a second narrow branch only when future intent has vacancy evidence and every candidate fact is an explicit unverified-gap fact that the paragraph itself discloses;
- verified skills, achievements, impact claims and mixed positive candidate evidence are never reclassified;
- interview answer-cardinality exception now recognizes resources/approaches in addition to examples/options/steps/reasons;
- factual durations, percentages, salaries, experience years and outcomes remain hard failures;
- RU/EN prompts are tightened to request `motivation` for disclosed-gap future learning and to prefer non-numeric response counts;
- Alice Final run #2 regression methods that were accidentally placed below `unittest.main()` are restored inside the test class;
- `evals/regressions/alice-final-run-3.json` captures exact run #3 failure patterns.

Offline replay of the retained run #3 raw responses under grounded-v2.5 is **8/8 PASS**, with 3 audited scenario repairs, 2 audited motivation-kind repairs, 0 unsupported numbers and 0 unsupported impact claims. Replay evidence: `docs/evidence/ai-bench-001/alice-final-run-3-grounded-v2.5-replay.json`. Replay is not a fresh provider result.

## 3. Historical Alice Final run #1 audit

Artifact содержит 8 raw responses, 8 presentation responses, `run.json`, `report.md` и pending manual-review template.

| Метрика | Значение |
|---|---:|
| API calls | 8/8 |
| Provider errors | 0 |
| Retries | 0 |
| Source machine pass | 6/8 |
| Mean quality | 0.960417 |
| Mean grounding | 0.979167 |
| Clean text | 1.000 |
| p50 | 4364.02 ms |
| p95 | 7399.02 ms |
| Estimated cost | USD 0.045921303 |

Все non-interview cases прошли. Оба FAIL локализованы в structured interview handling:

- RU: scenario `20%` использован без `s1` в том же `evidence_ids`; отдельно `2-3 примера` ошибочно классифицировано как factual numeric claim;
- EN: пять использований разрешённых `15%` / `90 days` не сопровождались соответствующим `s1` / `s2` в тех же question objects.

Это не transport/auth/schema failure и не новая cover-letter hallucination.

## 3. Grounded-v2.3 implementation audit

Изолированный `evals/` package теперь:

- сохраняет raw sanitized provider JSON без изменения в `responses/`;
- создаёт отдельный `machine/` слой для machine scoring;
- добавляет scenario ID только при exact normalized number -> exactly one scenario fact mapping;
- пишет каждый repair в audit metadata, не скрывая зависимость от deterministic post-processing;
- оставляет unknown/ambiguous provenance hard failure;
- различает non-factual response-cardinality instruction (`give 2 examples`, `приведите 2-3 примера`) и factual numeric assertion;
- сохраняет hard block для unsourced durations, percentages, salaries, experience numbers, impact/result numbers и прочих фактических чисел;
- усиливает RU/EN prompt: scenario fact используется не более одного раза и не должен повторяться между вопросами; numeric answer-count wording по возможности заменяется нечисловым;
- оставляет deterministic vacancy score, evidence semantics, impact safety, language gate, provider diagnostics, bounded retry и presentation marker cleanup без ослабления;
- final result checker принимает только benchmark/schema `1.4`, dataset `1.3.2`, единственного `yandex-alice-ai-llm`, 8/8 machine PASS, zero provider errors и zero unresolved hard-safety counters;
- не добавляет production AI route/service/model и не меняет migration schema.

## 4. Regression replay audit

Raw responses Alice Final run #1 replay-нуты через grounded-v2.3 локально без нового provider call.

- original: 6/8 PASS;
- replay: **8/8 PASS**;
- unique deterministic scenario provenance repairs: 6;
- unresolved scenario provenance violations: 0;
- unsupported numbers: 0.

Replay evidence: `docs/evidence/ai-bench-001/alice-final-run-1-grounded-v2.3-replay.json`.

Replay не заменяет fresh live verification, потому что обновлённые prompt instructions нельзя проверить на уже сохранённом ответе.

## 5. Local verification

| Check | Result |
|---|---|
| AI-BENCH package gate | PASS |
| Focused AI-BENCH unittest suite | 90 PASS |
| Deterministic grounded-v2.6.1 reference | 8/8 PASS |
| Dataset fingerprint | `4828033223fabd10a9442289708bbae0731054ce92595f63f1954940caad3e2f` |
| Cover-letter presentation violations in reference | 0 |
| Repository regression groups | 368 PASS, 14 environment-dependent skips, 24 subtests PASS |
| Repository hygiene | PASS after generated caches removed |

14 local skips require complete GitHub CI Flask/Psycopg/PostgreSQL dependencies and are not claimed as locally passed.

## 6. Production boundary

Изменения ограничены AI-BENCH runner/scoring/config/fixtures/regressions/tests/scripts, benchmark evidence и документацией. Production application files - `app.py`, runtime `config.py`, models, repositories, routes, production services, templates, static assets, migrations, requirements and Render manifests - не меняются для grounded-v2.6.1.

Production schema остаётся `20260819_0014`. GitHub/Yandex secret values отсутствуют в source и generated benchmark evidence.

## 7. Current gate

1. Green ordinary GitHub CI на v1.4.47 / evals 1.6.1.
2. При ordinary push billable Alice job должен быть skipped.
3. После green ordinary CI - manual `run_ai_bench_alice_final=true` на `main`.
4. Fresh run должен быть benchmark `1.4`, dataset `1.3.6`, contract `grounded-v2.6.1`, provider `yandex-alice-ai-llm` и дать **8/8 machine PASS**.
5. Все hard-safety/presentation counters должны оставаться zero; любые допустимые deterministic repairs должны быть audited.
6. Скачать artifact и проверить raw/machine/presentation evidence.
7. Провести focused named human re-review прежде всего cases 1, 3, 5 и 6 и проверить отсутствие regression в 2, 4, 7 и 8.
8. Только после этого закрывать `AI-BENCH-001` и разблокировать `AI-PROVIDER-001`.

## 8. Status decision

Historical run #5 machine gate - **8/8 COMPLETE**, named human gate - **REVISION REQUIRED**.  
`AI-BENCH-001 grounded-v2.6.1` - **НУЖНА ПРОВЕРКА** ordinary CI -> fresh Alice Final 8/8 -> focused named human re-review.  
Ранее завершённые production-пакеты остаются **ВЫПОЛНЕНО**.  
`AI-PROVIDER-001` остаётся **ЗАБЛОКИРОВАНО**.

## 9. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.38 | 26.08.2026 | Live run #1 reviewed; grounded-v2 prepared. |
| 1.4.39 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 prepared. |
| 1.4.40 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 comparative safety hardening prepared. |
| 1.4.41 | 27.08.2026 | Comparative live run #4 reviewed; Alice chosen as final candidate and dedicated Alice-only gate added. |
| 1.4.42 | 27.08.2026 | Alice Final run #1 reviewed: 8/8 transport, 6/8 source machine. Grounded-v2.3 adds auditable unique scenario-provenance normalization and narrow answer-cardinality classification; retained responses replay 8/8, fresh Alice-only live verification still required. |
| 1.4.46 | 13.09.2026 | Run #5 8/8 machine evidence + named human REVISION REQUIRED recorded; grounded-v2.6/evals 1.6.0 writing hardening prepared; ordinary CI -> fresh Alice Final -> focused named human re-review required. |

## 2026-08-28 - Alice Final v3 / grounded-v2.4

Artifact `ai-bench-20260827T112440Z-243eaaeb` completed 8/8 calls with zero provider errors/retries and machine result 6/8. The two confirmed contract issues are addressed without weakening hard safety gates: Unicode dash variants are normalized for lexical grounding; vacancy-only explicit future-intent `candidate_fit` paragraphs may be audibly reclassified to `motivation`; interview prompts explicitly require complete role-evidence coverage. Fresh Alice-only 8/8 live verification and named human writing review remain mandatory before closing AI-BENCH-001.
## v1.4.43 source delta

Source basis: current `main (27)` plus Alice Final artifact `33066898884`. The implementation delta is limited to AI-BENCH scoring/normalization, runner/reporting, interview fixtures/prompts, versioned regressions/tests/package checks, CI labels and canonical documentation. Production application files and database revision are unchanged.
## 2026-08-28 - Alice Final v4 / grounded-v2.5

### v1.4.44 source delta

Source basis: current `main (28)` plus Alice Final artifact `33163009779`. The implementation delta is limited to AI-BENCH scoring/normalization, RU/EN benchmark prompts, versioned regression/tests/package checks, workflow labels, replay evidence and canonical documentation. Production application files and database revision remain unchanged.


## 14.09.2026 addendum — run #6 / Neon staging recovery

- Alice Final run #6 artifact `34766480932`: 8/8 calls, 0 errors/retries, 7/8 machine; only `cover-letter-en-01` failed with 3 unsupported inferred impacts.
- Grounded-v2.6.1 keeps hard safety gates unchanged and tightens only English cover-letter generation plus regression coverage.
- Render Free PostgreSQL expired/suspended; Render web staging was re-pointed to Neon PostgreSQL in Oregon. `/health/ready` confirmed `status=ok`, persistent PostgreSQL and migration/revision `20260819_0014`. Old Render DB data was not migrated.
- No production application route/model/migration changes are introduced by this package.

| 1.4.47 | 14.09.2026 | Run #6 7/8 reviewed; grounded-v2.6.1/evals 1.6.1 atomic EN cover-letter hardening + Neon staging DB recovery documented; fresh Alice 8/8 and focused human re-review remain required. |

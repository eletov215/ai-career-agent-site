# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.16 |
| Дата | 14 сентября 2026 |
| Пакет | AI-BENCH-001 final closure / grounded-v2.6.1 |
| Статус | **ВЫПОЛНЕНО** - FINAL ALICE 8/8 + NAMED HUMAN PASS |
| Production revision | `20260819_0014` |

## 0. Final Alice run #7 + named human closure

Sanitized artifact `ai-bench-001-yandex-alice-final-34830877796.zip`:

| Метрика | Значение |
|---|---:|
| Run ID | `ai-bench-20260914T100639Z-222dfc87` |
| Benchmark / dataset / contract | `1.4` / `1.3.6` / `grounded-v2.6.1` |
| Provider | `yandex-alice-ai-llm` |
| API cases | **8/8 PASS** |
| Provider errors / retries | **0 / 0** |
| Mean quality | `0.998437` |
| Mean grounding | `0.984375` |
| Language / clean text / match consistency | `1.000 / 1.000 / 1.000` |
| Unsupported numbers | `0` |
| Unsupported impact claims | `0` |
| Forbidden claims | `0` |
| Cover-letter presentation violations | `0` |
| User-facing technical tokens | `0` |
| Scenario provenance violations | `0` |
| Audited scenario repairs / marker cleanup | `2 / 14` |
| p50 / p95 | `5605.601 ms / 10913.996 ms` |
| Estimated cost | `USD 0.055999992` |

Ordinary GitHub CI for grounded-v2.6.1 was confirmed green. The fresh live machine gate therefore satisfies the benchmark closure criteria without weakening any hard threshold.

Named reviewer **Шекунов Д.С.** completed the focused human re-review of the revised writing cases. The reviewer explicitly stated that the results are satisfactory and the package can be considered completed. A clarification was accepted that sparse benchmark source facts intentionally produce a shorter cover letter; richer confirmed profile/vacancy evidence may produce a more substantive letter, while the model must not invent details merely to increase length. No new numeric re-review scores were supplied, so none are recorded.

### Final decision

`AI-BENCH-001` - **ВЫПОЛНЕНО**.  
Alice AI LLM passes the accepted benchmark and human-writing gate and remains the primary candidate entering `AI-PROVIDER-001`. This is a benchmark decision, not production-provider activation. `AI-PROVIDER-001` is now **ГОТОВО К СТАРТУ**.

## 1. Alice Final run #6 + grounded-v2.6.1

Sanitized artifact `ai-bench-001-yandex-alice-final-34766480932.zip`:

- run ID `ai-bench-20260913T154901Z-44d67112`;
- benchmark `1.4`, dataset `1.3.5`, contract `grounded-v2.6`;
- provider `yandex-alice-ai-llm`;
- 8/8 API calls; provider errors 0; retries 0; **machine result 7/8**;
- mean quality `0.986458`; mean grounding `0.989583`; clean text `1.000`;
- p50 `3550.43 ms`; p95 `5611.53 ms`; estimated cost `USD 0.053826221`;
- all cases pass except `cover-letter-en-01`;
- `unsupported_impact_claim_count=3`; all other unresolved hard counters remain zero.

### Confirmed failure

The EN cover letter expanded sparse verified facts into unsupported propositions:

1. Figma/design systems -> `ensuring a cohesive visual language across products`;
2. qualitative interviews -> inferred design-decision/user-needs/product-direction effects;
3. product/engineering collaboration -> inferred implementation/delivery effects.

The hard scorer correctly rejected these claims. No threshold is weakened. The opening also included `I’ve long admired how your team approaches product design`, which invents prior employer familiarity not present in source facts; grounded-v2.6.1 adds a dedicated forbidden familiarity regression for that pattern.

### Grounded-v2.6.1 / evals 1.6.1

- dataset advances to `1.3.6`, contract to `grounded-v2.6.1`; benchmark/run schema stays `1.4`;
- English cover-letter candidate-fit prompt now requires short atomic first-person restatements of verified facts;
- purpose/benefit/result tails (`to...`, `which...`, `ensuring...`, `helping...`, `informing...`, `aligning...`, `bringing...`) are prohibited unless that proposition is explicitly in cited candidate evidence;
- invented context such as user needs, business goals, technical requirements, product direction, consistency, scalability and implementation quality is prohibited unless explicitly sourced;
- motivation can express present interest but cannot invent prior employer/team familiarity;
- exact run #6 failure patterns and safe literal rewrites are versioned in `evals/regressions/alice-final-run-6.json`;
- deterministic reference is 8/8 under dataset 1.3.6; production application and DB schema revision `20260819_0014` remain unchanged.

Next gate: ordinary GitHub CI/package gate -> fresh manual `run_ai_bench_alice_final=true` -> require 8/8 under dataset 1.3.6 / grounded-v2.6.1 -> focused named human re-review -> closure decision.

## 2. Подтверждённый Alice Final run #4

Sanitized artifact `ai-bench-001-yandex-alice-final-33165683757.zip` разобран полностью.

- run ID: `ai-bench-20260828T111023Z-62a5cc1a`;
- benchmark `1.4`, dataset `1.3.4`, contract `grounded-v2.5`;
- provider: `yandex-alice-ai-llm`;
- 8/8 API calls завершены; provider errors 0; retries 0;
- **machine result: 8/8 PASS**;
- mean quality `0.999479`; mean grounding `0.994792`; language `1.000`; match consistency `1.000`;
- p50 `3734.228 ms`; p95 `8872.01 ms`; estimated cost `USD 0.052416386`;
- invalid evidence IDs 0; unsupported numbers 0; unsupported impact claims 0; scenario provenance violations 0; user-facing technical-token hard failures 0.

The dedicated live machine gate is complete.

### Artifact audit finding

`interview-en-01` presentation retained two grouped known-ID decorations in user-facing `purpose` strings: `(c1, c2)` / `(v1, v2)` and `(c1, c2, v2)`. Existing grounded-v2.5 cleanup removed 13 simple one-ID markers but did not match a comma-separated group. This is a deterministic presentation sanitizer defect, not a provider grounding/safety failure.

### Artifact-sanitization hotfix r1 / evals 1.5.3

- grouped parenthesized/bracketed markers are cleaned only when the whole group contains known IDs separated by commas/semicolons;
- every removed ID is audited;
- mixed or unknown groups are never silently cleaned and remain hard metadata failures;
- prompts, provider I/O, machine evidence semantics, thresholds, production routes and schema are unchanged.

Retained raw run #4 responses replay: **8/8 PASS**, 3 scenario repairs, 20 marker cleanups, 0 residual evidence IDs in declared user-facing paths. Evidence: `docs/evidence/ai-bench-001/alice-final-run-4-presentation-replay.json`.

Local bounded repository verification: **358 passed, 14 environment-dependent skipped, 19 subtests passed**; AI-BENCH package gate PASS; repository hygiene PASS.

A second billable Alice run is not required for this presentation-only deterministic correction.

## 2. Подтверждённый Alice Final run #3

Sanitized artifact `ai-bench-001-yandex-alice-final-33163009779.zip` разобран полностью.

- run ID: `ai-bench-20260828T102540Z-bcf4c2ed`;
- benchmark `1.4`, dataset `1.3.3`, contract `grounded-v2.4`;
- provider: `yandex-alice-ai-llm`;
- 8/8 API calls завершены; provider errors 0; retries 0;
- source machine result: **6/8 PASS**;
- mean quality `0.975`; mean grounding `1.000`; clean text `1.000`;
- p50 `4796.74 ms`; p95 `11855.16 ms`; estimated cost `USD 0.051498352`.

FAIL #1 — `cover-letter-en-01`: paragraph with `c5` + `v3` correctly disclosed that experimentation is not verified, then expressed future learning (`eager to grow in this area`) but was labeled `candidate_fit`. The impact detector therefore saw unsupported `growth_increase`. There is no invented past achievement; this is a narrow paragraph-kind/intent mismatch.

FAIL #2 — `interview-ru-01`: phrase `Назовите 2–3 ресурса или подхода...` triggered unsupported numbers `2` and `3`. This is answer cardinality, not a factual duration, percentage, experience, salary or result.

## 2. Grounded-v2.5 / Alice Final v4

`evals 1.5.2`, benchmark `1.4`, dataset `1.3.4`, contract `grounded-v2.5` introduces only two narrow corrections plus one test-discovery fix:

1. `candidate_fit -> motivation` may be repaired only for explicit future intent with vacancy evidence and either zero candidate evidence or candidate evidence consisting exclusively of explicit unverified-gap facts disclosed in the same paragraph. Verified skills/achievements/impact remain hard failures.
2. Interview response-cardinality recognizes counts of resources/approaches in the same narrow imperative class as examples/options/steps/reasons. Unsourced factual numbers remain hard failures.
3. Alice Final run #2 regression methods are moved back inside the unittest class; ordinary CI now executes them instead of silently skipping them.

RU/EN benchmark prompts are tightened consistently. No production AI integration is added.

## 3. Offline replay Alice Final run #3

The retained raw responses were replayed without a provider call:

- source: 6/8;
- grounded-v2.5 replay: **8/8**;
- scenario-provenance repairs: 3;
- motivation-kind repairs: 2;
- unsupported numbers: 0;
- unsupported impact claims: 0.

Evidence: `docs/evidence/ai-bench-001/alice-final-run-3-grounded-v2.5-replay.json`. This replay does not validate the updated prompt and cannot close AI-BENCH-001.

## 4. Historical evidence

### Alice Final run #1

Sanitized artifact `ai-bench-001-yandex-alice-final-33061758538.zip` разобран полностью.

- run ID: `ai-bench-20260827T101353Z-bd9809d6`;
- benchmark `1.3`, dataset `1.3.1`, contract `grounded-v2.2`;
- provider: `yandex-alice-ai-llm`;
- 8/8 API calls завершены;
- provider errors: 0;
- retries: 0;
- source machine result: **6/8 PASS**;
- mean quality: `0.960417`;
- mean grounding: `0.979167`;
- clean text: `1.000`;
- p50: `4364.02 ms`;
- p95: `7399.02 ms`;
- estimated cost: `USD 0.045921303`.

Resume analysis RU/EN, vacancy match RU/EN и cover letter RU/EN прошли. Оба FAIL относятся к interview cases.

## 2. Root cause двух FAIL

### 2.1 `interview-ru-01`

Фактический scenario `20%` был использован в `follow_up_if_weak`, но `s1` отсутствовал в `evidence_ids` того же question object. При этом другой scenario `30 дней` был корректно связан с `s2`.

Дополнительно модель написала `Приведите 2–3 конкретных примера`. Старый generic numeric gate посчитал `2` и `3` неподтверждёнными числами. Это false positive: фраза задаёт количество элементов ответа и не утверждает срок, зарплату, опыт, процент, достижение или иной факт кандидата.

### 2.2 `interview-en-01`

Все использованные `15%` и `90 days` были разрешёнными scenario facts, но пять question objects не включили соответствующие `s1`/`s2` в structured `evidence_ids`. Unsupported factual numbers, provider errors, schema errors и language violations отсутствовали.

Вывод: run #1 выявил устойчивый structured-metadata defect Alice, а также один дефект классификации числа в benchmark. Ослаблять global safety thresholds не требуется.

## 3. Grounded-v2.3 / Alice Final v2

`evals 1.5.0`, benchmark `1.4`, dataset `1.3.2`, contract `grounded-v2.3` вводит две точечные и проверяемые корректировки.

1. **Deterministic scenario provenance normalization.** Runner сохраняет raw provider response без изменений и создаёт отдельную machine-scored copy. Если exact normalized number внутри одного interview question однозначно соответствует ровно одному `kind=scenario` fact, machine layer может добавить только этот `sN` в structured `evidence_ids`. Repair записывается в `normalization.scenario_provenance_repairs` с path/number/evidence ID. Unknown или ambiguous mapping не repair-ится и остаётся hard failure.
2. **Narrow answer-cardinality classification.** Только строго ограниченные interview imperatives вида `give/provide/name/list N examples/options/steps/reasons` и `приведите/назовите/перечислите N примеров/вариантов/шагов/причин` считаются response-format instruction, а не factual claim. Unsourced duration, percentage, salary, experience year, result и другие numeric claims по-прежнему блокируются.

Дополнительно RU/EN interview prompt требует использовать каждый scenario fact не более одного раза, не повторять scenario numbers и по возможности формулировать answer-count инструкции без числа.

## 4. Аудируемость нормализации

Каждый run теперь имеет три уровня evidence:

- `responses/<provider>/<case>.json` - raw sanitized provider JSON, неизменённый;
- `machine/<provider>/<case>.json` - copy после только deterministic one-to-one scenario provenance normalization; именно она проходит machine scoring;
- `presentation/<provider>/<case>.json` - presentation copy после machine normalization и удаления только простых decorated known markers `(s1)` / `[c1]`.

Нормализация не изменяет пользовательскую семантику, не переписывает impact claims, не исправляет unknown evidence IDs и не добавляет candidate/vacancy facts. Ambiguous scenario numbers остаются hard failures. Raw response SHA и machine/presentation SHA сохраняются раздельно.

## 5. Regression replay Alice Final run #1

Те же raw responses из artifact `33061758538` повторно оценены локально новым deterministic layer без нового API вызова.

| Метрика | Исходный run | grounded-v2.3 replay |
|---|---:|---:|
| Cases PASS | 6/8 | **8/8** |
| Provider errors | 0 | 0 |
| Scenario provenance repairs | n/a | 6 |
| Unresolved scenario provenance violations | 6 | **0** |
| Unsupported numbers | 2 | **0** |

Replay machine-readable evidence: `docs/evidence/ai-bench-001/alice-final-run-1-grounded-v2.3-replay.json`.

Это **не новый provider result**. Replay доказывает correctness новой deterministic normalization/scoring policy на сохранённых response bodies, но не проверяет обновлённый prompt. Fresh Alice-only live run обязателен.

## 6. Local verification package

- focused AI-BENCH unittest suite: **90 PASS**;
- repository test modules in three bounded groups: **368 PASS**, **14 environment-dependent SKIP**, **24 subtests PASS**, 0 confirmed failures;
- deterministic grounded-v2.6.1 reference: **8/8 PASS**;
- reference dataset fingerprint: `4828033223fabd10a9442289708bbae0731054ce92595f63f1954940caad3e2f`;
- cover-letter presentation violations in deterministic reference: **0**;
- AI-BENCH package gate: PASS;
- repository hygiene: PASS after generated caches removed;
- production application boundary and schema revision `20260819_0014`: unchanged.

14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed.

## 7. Closure gate

1. Ordinary GitHub CI for grounded-v2.6.1 - **PASS**.
2. Fresh Alice Final run on dataset `1.3.6` / `grounded-v2.6.1` - **8/8 PASS**.
3. Artifact audit - **PASS**, zero unresolved hard counters.
4. Focused named human re-review by **Шекунов Д.С.** - **PASS**.
5. Owner closure decision - **APPROVED**.

The package has no remaining verification gate. Next package: `AI-PROVIDER-001`.

## 8. Status decision

`AI-BENCH-001` - **ВЫПОЛНЕНО**.  
Final machine gate - **8/8 PASS**.  
Named human writing gate - **PASS**.  
`AI-PROVIDER-001` - **ГОТОВО К СТАРТУ**.

## 9. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.16 | 14.09.2026 | Final Alice artifact `34830877796`: 8/8 PASS, zero hard counters; named reviewer Шекунов Д.С. accepted focused re-review; AI-BENCH-001 COMPLETE, AI-PROVIDER-001 READY. |
| 1.6 | 26.08.2026 | Green CI + live run #1 reviewed; grounded-v2 prepared. |
| 1.7 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 added language/scenario/motivation/diagnostic/retry hardening. |
| 1.8 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 added source-matched impact safety and presentation-only marker repair. |
| 1.9 | 27.08.2026 | Comparative live run #4 reviewed; Alice selected as final candidate and dedicated Alice-only 8/8 gate added. |
| 1.10 | 27.08.2026 | Alice Final run #1 artifact `33061758538` reviewed: 8/8 transport, 6/8 raw machine. Grounded-v2.3 adds auditable unique scenario-provenance normalization, narrow response-cardinality classification and requires a fresh Alice-only verification before human review. |
| 1.12 | 28.08.2026 | Alice Final run #3 reviewed; grounded-v2.5 hotfix/replay 8/8 prepared; fresh live gate still pending. |
| 1.13 | 28.08.2026 | Alice Final run #4 artifact `33165683757`: 8/8 live machine PASS, 0 errors/retries. Artifact audit found grouped known evidence markers in two user-facing EN interview purpose strings. Evals 1.5.3 adds deterministic grouped-marker sanitation; retained raw replay remains 8/8 with 20 cleanups and 0 residual user-facing IDs. Remaining gate: ordinary CI + named human rubric. |
| 1.14 | 13.09.2026 | Run #5 8/8 machine evidence + named human REVISION REQUIRED recorded; grounded-v2.6/evals 1.6.0 writing hardening candidate prepared; fresh Alice + focused human re-review required. |
| 1.15 | 14.09.2026 | Alice Final run #6 artifact `34766480932`: 8/8 transport, 7/8 machine; EN cover letter failed on 3 unsupported inferred effects. Grounded-v2.6.1/evals 1.6.1 atomic candidate-fit and employer-familiarity hardening prepared; fresh Alice 8/8 + focused human re-review required. |

## 2026-08-28 - Alice Final v3 / grounded-v2.4

Artifact `ai-bench-20260827T112440Z-243eaaeb` completed 8/8 calls with zero provider errors/retries and machine result 6/8. The two confirmed contract issues are addressed without weakening hard safety gates: Unicode dash variants are normalized for lexical grounding; vacancy-only explicit future-intent `candidate_fit` paragraphs may be audibly reclassified to `motivation`; interview prompts explicitly require complete role-evidence coverage. Fresh Alice-only 8/8 live verification and named human writing review remain mandatory before closing AI-BENCH-001.
## Alice Final run #2 and grounded-v2.4

Run `ai-bench-20260827T112440Z-243eaaeb` completed 8/8 calls with zero errors/retries and scored 6/8. `cover-letter-ru-01` failed because a vacancy-only explicit future-intent paragraph was mislabeled `candidate_fit`; `interview-ru-01` failed partly because Unicode non-breaking hyphens prevented lexical grounding of `тест‑кейсы` and because v1/v2 were absent from structured evidence. Grounded-v2.4 fixes those contract mismatches narrowly and audibly; existing-skill claims, missing evidence, invalid IDs and unsupported impact remain hard failures. Fresh 8/8 Alice-only verification is required before named human review.


## 2026-08-28 - Alice Final v4 / grounded-v2.5

Artifact `33163009779` / run `ai-bench-20260828T102540Z-bcf4c2ed` completed 8/8 calls with zero provider errors/retries and machine result 6/8. Grounded-v2.5 addresses only the confirmed paragraph-kind/intent and response-cardinality mismatches, restores run #2 regression test discovery, and replays the retained raw responses 8/8. Fresh Alice-only 8/8 live verification plus named human writing review remain mandatory.








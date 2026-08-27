# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.10 |
| Дата | 27 августа 2026 |
| Пакет | AI-BENCH-001 Alice Final v2 / grounded-v2.3 provenance normalization |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS + FRESH ALICE-ONLY MACHINE RUN + NAMED MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. Подтверждённый Alice Final run #1

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

- AI-BENCH unit/package suite: **70 PASS**;
- full repository test modules в четырёх bounded groups: **348 PASS**, **14 environment-dependent SKIP**, **15 subtests PASS**, 0 confirmed failures;
- deterministic grounded-v2.3 reference: **8/8 PASS**;
- reference dataset fingerprint: `c0d6946af29356f8e19abdb1178beac3428752f7985d33d78f2ab01b9edc7b2f`;
- AI-BENCH package gate: PASS;
- repository hygiene: PASS after generated caches removed;
- infrastructure manifest: PASS;
- SQLite migration chain `0001 -> 0014`: PASS;
- Alembic current/check: `20260819_0014` / PASS;
- production application boundary: unchanged.

14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed.

## 7. Remaining external gate

1. Upload v1.4.42 through the normal GitHub PR/CI path.
2. Require green `Python tests`, `AI-BENCH-001 package gate` and all historical gates.
3. On ordinary push the billable Alice job must remain skipped.
4. Run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true` on `main`.
5. Require benchmark `1.4`, dataset `1.3.2`, exactly one provider `yandex-alice-ai-llm`, 8/8 machine PASS, zero provider errors and zero unresolved hard-safety counters.
6. Scenario provenance repair count may be non-zero only when every repair is the audited unique exact-number mapping defined by grounded-v2.3; the count remains visible in report/run evidence.
7. Download the sanitized artifact and review raw/machine/presentation differences.
8. Only after machine 8/8 complete the named human writing-quality rubric.
9. Record AI-BENCH-001 closure decision; only then unblock `AI-PROVIDER-001`.

## 8. Status decision

`AI-BENCH-001` remains **НУЖДАЕТСЯ ВО ВНЕШНЕЙ ПРОВЕРКЕ**.  
Alice AI LLM remains the **PRIMARY CANDIDATE**, not yet a production provider.  
`AI-PROVIDER-001` remains **BLOCKED**.  
No production AI provider is connected.

## 9. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.6 | 26.08.2026 | Green CI + live run #1 reviewed; grounded-v2 prepared. |
| 1.7 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 added language/scenario/motivation/diagnostic/retry hardening. |
| 1.8 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 added source-matched impact safety and presentation-only marker repair. |
| 1.9 | 27.08.2026 | Comparative live run #4 reviewed; Alice selected as final candidate and dedicated Alice-only 8/8 gate added. |
| 1.10 | 27.08.2026 | Alice Final run #1 artifact `33061758538` reviewed: 8/8 transport, 6/8 raw machine. Grounded-v2.3 adds auditable unique scenario-provenance normalization, narrow response-cardinality classification and requires a fresh Alice-only verification before human review. |

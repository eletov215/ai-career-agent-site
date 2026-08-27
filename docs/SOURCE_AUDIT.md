# AI Career Agent - аудит источников v1.4.42

**Дата:** 27.08.2026  
**Production revision:** `20260819_0014`

| Поле | Значение |
|---|---|
| Проверяемая кодовая основа | `ai-career-agent-site-main (26).zip` |
| ZIP comment | `49b648cd304479d55fc23ef243c6b9c0abdeaaec` |
| Проверяемый пакет | AI-BENCH-001 Alice Final v2 / grounded-v2.3 provenance normalization |
| Evals | `1.5.0` |
| Benchmark contract | `1.4` |
| Dataset | `ai-career-agent-golden-v1` v`1.3.2`, `contract=grounded-v2.3` |
| External evidence | Alice Final run #1 artifact `33061758538`; run ID `ai-bench-20260827T101353Z-bd9809d6` |
| Результат | локальный candidate готов; нужен ordinary GitHub CI + fresh Alice-only 8/8 machine run + named manual rubric |

## 1. Source precedence

Пользователь предоставил `ai-career-agent-site-main (26).zip` как актуальный snapshot GitHub `main`. Для этой поставки он имеет приоритет над всеми предыдущими архивами. Sanitized artifact `ai-bench-001-yandex-alice-final-33061758538.zip` используется только как внешнее benchmark evidence. Secret values и production user data в репозиторий не копируются.

Сравнение `main (26)` с ранее выданным v1.4.41 full delivery показало одинаковый набор из 392 файлов и отсутствие byte-level различий; следовательно, run #1 действительно относится к текущей кодовой основе перед v1.4.42.

## 2. Alice Final run #1 audit

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
| AI-BENCH unit/package suite | 70 PASS |
| Deterministic reference | 8/8 PASS |
| Dataset fingerprint | `c0d6946af29356f8e19abdb1178beac3428752f7985d33d78f2ab01b9edc7b2f` |
| Repository regression groups | 348 PASS, 14 environment-dependent skips, 15 subtests PASS |
| Repository hygiene | PASS after generated caches removed |
| Infrastructure manifest | PASS |
| SQLite migrations | `0001 -> 0014` PASS; current/check `20260819_0014` |

14 local skips require complete GitHub CI Flask/Psycopg/PostgreSQL dependencies and are not claimed as locally passed.

## 6. Production boundary

Изменения ограничены AI-BENCH runner/scoring/config/fixtures/regressions/tests/scripts, benchmark evidence и документацией. Production application files - `app.py`, runtime `config.py`, models, repositories, routes, production services, templates, static assets, migrations, requirements and Render manifests - не требуют изменения для grounded-v2.3.

Production schema остаётся `20260819_0014`. GitHub/Yandex secret values отсутствуют в source и generated benchmark evidence.

## 7. Current gate

1. Green ordinary GitHub CI на v1.4.42.
2. При ordinary push billable Alice job должен быть skipped.
3. Manual `run_ai_bench_alice_final=true` на `main`.
4. Fresh run должен быть benchmark `1.4`, dataset `1.3.2`, provider `yandex-alice-ai-llm` и дать 8/8 machine PASS.
5. Scenario repairs допускаются только как audited one-to-one repairs; unresolved safety counters должны оставаться zero.
6. Скачать artifact и проверить raw/machine/presentation evidence.
7. Завершить named human writing-quality rubric.
8. Только после этого закрывать `AI-BENCH-001` и разблокировать `AI-PROVIDER-001`.

## 8. Status decision

`AI-BENCH-001 Alice Final v2` - **НУЖНА ПРОВЕРКА**.  
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

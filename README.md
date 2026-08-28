# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-28

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - Alice Final v4 / `grounded-v2.5`; локальный hotfix готов, НУЖНА ПРОВЕРКА GITHUB ACTIONS + FRESH ALICE-ONLY LIVE + NAMED MANUAL RUBRIC |
| Alice Final run #3 | artifact `33163009779`, run `ai-bench-20260828T102540Z-bcf4c2ed`: 8/8 calls, 0 errors/retries; source machine result 6/8 |
| Подтверждённые FAIL | `cover-letter-en-01`: future-learning gap paragraph mislabeled `candidate_fit`; `interview-ru-01`: harmless `2–3 resources/approaches` answer-cardinality false positive |
| Regression replay | те же raw responses под `grounded-v2.5`: 8/8 PASS, 3 scenario repairs, 2 motivation-kind repairs, 0 unsupported numbers/impact |
| Candidate decision | Alice AI LLM остаётся primary candidate; provider decision не финализирован до fresh machine 8/8 + named human rubric |
| Hardening | `evals 1.5.2`, benchmark `1.4`, dataset `1.3.4` / `grounded-v2.5`; narrow unverified-gap motivation repair + broader safe response-cardinality + restored run #2 unittest discovery |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_alice_final=true` -> fresh Alice 8/8 machine artifact -> named human writing rubric -> benchmark closure decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.44`, PROJECT PASSPORT `v2.58`, SOURCE AUDIT `v1.4.44`, AI-BENCH verification `v1.12` |

Production Flask routes, dependencies, models, migrations, Render runtime and database schema are unchanged. Benchmark fixtures remain synthetic and credentials remain GitHub-secret-only.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Назначение

AI Career Agent — Flask/Gunicorn web-service карьерного сопровождения:

```text
аккаунт -> резюме -> подтверждённый профиль -> AI-анализ
-> вакансии -> объяснимый match -> сопроводительное письмо -> tracker
```

Реальный production AI пока не подключён. Текущий `evals/` package предназначен для воспроизводимого выбора AI-моделей до интеграции в пользовательские routes.

## 2. Runtime

- WSGI entrypoint: `app:app`;
- production database: PostgreSQL через SQLAlchemy/Alembic;
- current production revision: `20260819_0014`;
- local/test fallback: SQLite;
- web, Trudvsem sync worker и privacy cleanup worker разделены на процессы;
- Render остаётся staging/резервным контуром до предрелизной VPS-миграции.

## 3. AI-BENCH-001 Alice final verification

`evals 1.5.2` uses benchmark `1.4` / dataset `1.3.4` / `grounded-v2.5`. It is the local hotfix after Alice Final run #3 (`33163009779`) completed all 8 provider calls with zero errors/retries but passed 6/8 machine cases.

- `cover-letter-en-01` exposed a paragraph-kind mismatch: the model disclosed the unverified experimentation gap and expressed future learning, but labeled the paragraph `candidate_fit`; grounded-v2.5 may reclassify it to `motivation` only when vacancy evidence exists and every candidate fact is an explicit unverified-gap fact disclosed in the paragraph;
- verified skills, achievements, mixed positive candidate evidence and unsupported impact are never repaired;
- `interview-ru-01` exposed a narrow answer-cardinality false positive on `2–3 resources or approaches`; imperative counts of resources/approaches now share the same non-factual response-format exception as examples/options/steps/reasons;
- unsourced durations, percentages, salaries, experience years, achievements and outcomes remain hard failures;
- the retained raw run #3 responses replay 8/8 under grounded-v2.5 with 3 audited scenario repairs and 2 audited motivation-kind repairs; replay is not a new provider result;
- the run #2 regression tests are now inside the unittest class and are executed by ordinary CI;
- ordinary CI remains non-billable. `AI-BENCH-001 Alice Final` runs only on manual `workflow_dispatch` with `run_ai_bench_alice_final=true`;
- the final checker requires benchmark/schema `1.4`, dataset `1.3.4`, exactly one `yandex-alice-ai-llm` provider, zero provider errors, 8/8 machine PASS and zero unresolved hard-safety counters;
- machine pass still does not close AI-BENCH-001: a named human writing-quality rubric remains mandatory.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench*.py' -v
```

After green ordinary CI, run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true`. The retained 6/8 run #3 artifact is regression evidence only and must not be reused as the final live result.

## 4. Документация

- `docs/PLAN_CURRENT.md` — канонический порядок работ;
- `docs/PROJECT_PASSPORT.md` — архитектура и границы продукта;
- `docs/SOURCE_AUDIT.md` — аудит текущего hotfix;
- `docs/AI_BENCH_VERIFICATION_STATUS.md` — failure evidence, root cause и gates;
- `docs/evidence/ai-bench-001/` — deterministic validation/reference evidence.

## 5. Security and release hygiene

Repository/release ZIP не должен содержать `.env`, реальные credentials/tokens, databases, dumps, backups, virtualenv, caches, bytecode или runtime benchmark artifacts. API credentials задаются только через environment/secret storage.

## 6. Hosting roadmap

Render остаётся staging/резервной площадкой. Реальная аренда и полевой тест VPS выполняются в `INFRA-001` перед beta; далее следуют HOST-001, OPS-002, DOMAIN-001, MIG-001 и REL-001.
## Alice Final v4 - grounded-v2.5

Alice Final run #3 (`ai-bench-20260828T102540Z-bcf4c2ed`, artifact `33163009779`) completed 8/8 provider calls with zero errors/retries and scored 6/8. The two failures are new narrow benchmark-contract mismatches rather than transport/schema failures: an explicitly disclosed unverified experimentation gap plus future-learning intent was labeled `candidate_fit`, and an interview request for `2–3 resources or approaches` was treated as a factual number. Grounded-v2.5 repairs only those cases under strict predicates, restores the run #2 regression methods to ordinary unittest discovery, and keeps verified skill/impact and factual-number safety gates hard. Offline replay of the retained raw run #3 responses is 8/8; a fresh Alice-only live verification is still required.


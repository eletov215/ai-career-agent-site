# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-09-14

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - Alice Final v4 / `grounded-v2.6.1`; НУЖНА ПРОВЕРКА ordinary CI + fresh Alice-only live 8/8 + focused named human re-review |
| Alice Final run #6 | artifact `34766480932`, run `ai-bench-20260913T154901Z-44d67112`: 8/8 calls, 0 errors/retries; machine result **7/8** |
| Подтверждённый FAIL | только `cover-letter-en-01`: 3 unsupported impact claims from inferred consistency/decision/implementation effects |
| Additional writing issue | opening invented prior employer familiarity (`long admired...`); grounded-v2.6.1 blocks that pattern unless source evidence supports it |
| Hardening | `evals 1.6.1`, benchmark `1.4`, dataset `1.3.6` / `grounded-v2.6.1`; atomic EN candidate-fit prompt + run #6 regressions; hard safety thresholds unchanged |
| Staging database | Render web-service now uses Neon PostgreSQL (Oregon) after Render Free Postgres expiry; `/health/ready` confirmed `status=ok`, persistent PostgreSQL, revision/migrations `20260819_0014` |
| Candidate decision | Alice AI LLM remains primary candidate; provider decision is not final until fresh machine 8/8 + named human rubric |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_alice_final=true` -> fresh Alice 8/8 machine artifact -> focused human review of cases 1/3/5/6 -> benchmark closure decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.47`, PROJECT PASSPORT `v2.61`, SOURCE AUDIT `v1.4.47`, AI-BENCH verification `v1.15` |

Production Flask routes, dependencies, models, migrations and database schema are unchanged. Benchmark fixtures remain synthetic and credentials remain secret-store-only.
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

`evals 1.6.1` uses benchmark `1.4` / dataset `1.3.6` / `grounded-v2.6.1`. It is the regression-driven hotfix after Alice Final run #6 (`34766480932`) completed all 8 provider calls with zero errors/retries but passed 7/8 machine cases.

- `cover-letter-en-01` was the only FAIL: the model converted verified Figma/design-system, interview and collaboration activities into unsupported consistency, decision/user-need and implementation outcomes;
- the existing hard scorer correctly blocked all three inferred effects; thresholds are not weakened and output is not auto-repaired;
- the opening also invented prior employer familiarity (`long admired...`), so the EN cover-letter case now explicitly forbids unsupported familiarity history;
- grounded-v2.6.1 tightens English candidate-fit generation to short atomic first-person restatements of cited candidate facts and prohibits purpose/benefit/result tails unless explicitly stated in evidence;
- deterministic reference remains 8/8 under the new dataset; exact run #6 patterns are versioned in `evals/regressions/alice-final-run-6.json`;
- ordinary CI remains non-billable. `AI-BENCH-001 Alice Final` runs only on manual `workflow_dispatch` with `run_ai_bench_alice_final=true`;
- the final checker now requires dataset `1.3.6`, exactly one `yandex-alice-ai-llm` provider, zero provider errors, 8/8 machine PASS and zero unresolved hard-safety counters;
- machine pass still does not close AI-BENCH-001: focused named human writing review remains mandatory.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench*.py' -v
```

After green ordinary CI, run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true`. The 7/8 run #6 artifact is regression evidence only and must not be reused as the final live result.

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


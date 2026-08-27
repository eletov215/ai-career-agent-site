# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-27

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - Alice Final v2 / provenance normalization; НУЖНА ПРОВЕРКА GITHUB ACTIONS + FRESH ALICE-ONLY LIVE + NAMED MANUAL RUBRIC |
| Alice Final run #1 | artifact `33061758538`: 8/8 calls, 0 errors/retries; source machine result 6/8; оба FAIL локализованы в interview provenance/number-classification |
| Regression replay | те же raw responses под `grounded-v2.3`: 8/8 PASS, 6 однозначных scenario-evidence repairs, 0 unresolved provenance, 0 unsupported numbers |
| Candidate decision | Alice AI LLM остаётся primary candidate; provider decision не финализирован до machine 8/8 + named human rubric |
| Hardening | `evals 1.5.0`, benchmark `1.4`, dataset `1.3.2` / `grounded-v2.3`: auditable unique scenario-provenance repair + narrow answer-cardinality numeric exception + prompt de-duplication |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_alice_final=true` -> fresh Alice 8/8 machine artifact -> named human writing rubric -> benchmark closure decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.42`, PROJECT PASSPORT `v2.56`, SOURCE AUDIT `v1.4.42`, AI-BENCH verification `v1.10` |

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

`evals 1.5.0` moves the final Alice candidate to benchmark `1.4` / dataset `1.3.2` / `grounded-v2.3` after Alice Final run #1 exposed two machine-contract defects rather than new provider transport problems:

- the raw Alice run completed 8/8 calls with zero errors/retries, but both interview cases omitted some `sN` provenance for scenario numbers;
- one RU follow-up asked for `2-3` examples, which the previous generic number detector incorrectly treated as a factual numeric claim;
- raw provider JSON is still retained in `responses/`; a separate deterministic `machine/` copy may append a scenario ID only when an exact normalized number maps to exactly one `kind=scenario` fact; every repair is audited;
- unknown or ambiguous numbers are never repaired and remain hard failures; unsupported durations/percentages/experience/impact numbers remain blocked;
- a tightly-scoped interview response-count phrase such as `give 2 examples` is treated as answer formatting, not a candidate/scenario fact;
- RU/EN interview prompts now ask the model to use each scenario fact at most once, avoid repeated scenario numbers, and prefer non-numeric wording for answer-count instructions;
- the retained Alice Final run #1 responses replay 8/8 under grounded-v2.3 with six audited scenario-provenance repairs and zero unresolved safety violations; this replay is not a new provider result;
- ordinary CI remains non-billable. `AI-BENCH-001 Alice Final` still runs only on manual `workflow_dispatch` with `run_ai_bench_alice_final=true`;
- the final checker now rejects old benchmark/dataset versions and still requires exactly one Alice provider, zero provider errors, all eight machine cases PASS and zero unresolved hard-safety counters;
- machine pass still does not close AI-BENCH-001: the named human writing-quality rubric remains mandatory.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench*.py' -v
```

After green ordinary CI, run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true`. Do not reuse the old 6/8 artifact as the final provider result; it is regression evidence only.

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

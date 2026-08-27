# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-27

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - Alice AI LLM final candidate hardening; НУЖНА ПРОВЕРКА GITHUB ACTIONS + ALICE-ONLY LIVE + NAMED MANUAL RUBRIC |
| Comparative live run #4 | artifact `33050972910`: 24/24 calls, 0 errors/retries; Alice 5/8, Flash 5/8, YandexGPT Pro 4/8 under grounded-v2.2 |
| Candidate decision | Alice AI LLM остаётся primary candidate; Flash - возможный future economy/low-risk option; YandexGPT Pro 5.1 не является leading primary candidate |
| Hardening | `evals 1.4.1`, benchmark `1.3`, dataset `1.3.1` / `grounded-v2.2`: final prompt audit, causal-impact guard, live-run-4 regressions, dedicated Alice-only final job |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_alice_final=true` -> Alice 8/8 machine artifact -> named human writing rubric -> benchmark closure decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.41`, PROJECT PASSPORT `v2.55`, SOURCE AUDIT `v1.4.41`, AI-BENCH verification `v1.9` |

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

`evals 1.4.1` keeps the grounded-v2.2 machine contract but hardens generation instructions after comparative live run #4:

- Alice AI LLM is the only provider in `evals/config/yandex-alice-final.json`; the historical three-provider comparison remains available separately through `run_ai_bench_live`;
- cover-letter prompts now require literal evidence-bound phrasing and explicitly rewrite unsupported causal/outcome language into neutral descriptions of verified actions;
- causal language is tracked as an independent impact-safety family even when another impact family appears in the same paragraph;
- interview prompts require a final per-question audit so every scenario number used in `question`, `purpose`, or `follow_up_if_weak` has its matching `sN` in the same `evidence_ids`;
- exact failures from live run #4 are versioned in `evals/regressions/live-run-4.json`; safe literal rewrites are protected against false positives;
- ordinary CI remains non-billable. The dedicated `AI-BENCH-001 Alice Final` job runs only on manual `workflow_dispatch` with `run_ai_bench_alice_final=true` and only after `Python tests` plus the deterministic AI-BENCH package gate pass;
- the Alice final gate requires exactly one provider, zero transport errors, all eight cases machine-pass, and zero hard safety counters;
- machine pass still does not close AI-BENCH-001: the named human writing-quality rubric remains mandatory.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

After green ordinary CI, run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true`. Do not run the full three-provider comparison again unless a regression investigation specifically requires it.

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

# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-26

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - grounded-v2.2 final safety hardening candidate; НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #4 + MANUAL RUBRIC |
| Ordinary CI | grounded-v2.1 v1.4.39 прошёл ordinary CI на `main` перед live run #3; текущий v2.2 candidate требует нового green CI |
| Live run #1 | artifact `32958938365`: 24/24 API calls, 0 errors; использован для grounded-v2 hardening |
| Live run #2 | artifact `32972783843`: Alice 5/8, Flash 4/8, YandexGPT Pro 3/8; один provider error; использован для grounded-v2.1 |
| Live run #3 | artifact `32978362483`: Alice 7/8, Flash 4/8, YandexGPT Pro 5/8, 24/24 calls без provider errors; manual review выявил unsupported impact в machine-passed Alice cover letter |
| Hardening | `evals 1.4.0`, benchmark `1.3`, dataset `1.3.0` / `grounded-v2.2`: source-matched impact families, live-run-3 regressions, post-score presentation sanitizer for simple decorated evidence IDs |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_live=true` -> live run #4 artifact -> named human writing rubric -> benchmark closure decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.40`, PROJECT PASSPORT `v2.54`, SOURCE AUDIT `v1.4.40`, AI-BENCH verification `v1.8` |

Production Flask routes, dependencies, models, migrations, Render runtime and database schema are unchanged. The benchmark continues to use synthetic fixtures only and GitHub-secret-only credentials.
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

## 3. AI-BENCH-001 grounded-v2.2 benchmark

`evals 1.4.0` is the final safety-hardening candidate after manual review of live run #3:

- Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1 remain the approved comparison set;
- exact raw evidence IDs, structured unverified facts/caveats, deterministic vacancy scoring, language/scenario/claim-evidence gates and safe provider diagnostics remain mandatory;
- cover-letter outcome claims are now checked by semantic impact family against the cited candidate evidence, so inferred speed, efficiency or service-quality gains are rejected unless the source facts contain the same impact family;
- the real unsupported Alice phrases found in live run #3 are versioned in `evals/regressions/live-run-3.json`;
- simple decorated known evidence markers such as `(s1)` or `[c1]` are recorded as repairable presentation noise, but scoring always evaluates the original payload first;
- `presentation/<provider>/<case>.json` removes only those simple decorated markers after scoring; missing evidence, unknown IDs, `evidence_ids:` labels and serialized schema/debug metadata remain hard failures;
- scenario provenance remains hard: removing `(s1)` from visible text never satisfies a missing structured `s1` citation;
- live providers still use safe envelope diagnostics and at most one bounded retry for configured transient/malformed failures;
- live job remains integrated into `.github/workflows/ci.yml`, runs only via manual `workflow_dispatch` with `run_ai_bench_live=true`, and waits for ordinary tests/package gate;
- runtime output remains outside the repository at `/tmp/ai-bench-yandex-live` and credentials are read only from GitHub Actions Secrets.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

After green ordinary CI run the manual live benchmark and review its artifact. A green transport job is not enough to select a provider: the final accepted candidate must also pass machine safety review and the named human writing-quality rubric.

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

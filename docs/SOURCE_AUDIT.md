# AI Career Agent — аудит источников v1.4.37

<!-- ACA-CANONICAL-STATUS:START -->
## Канонический аудит — 2026-08-26

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.37 |
| Проверяемый пакет | AI-BENCH-001 stability hotfix r4 |
| Исходный код | `ai-career-agent-site-eletov215-patch-1 (1).zip`, актуальный GitHub archive после run #201 |
| Production revision | `20260819_0014` |
| Результат | workflow-context defect локализован и исправлен; ordinary GitHub CI требуется повторить |

Run #201 не является regression предыдущих product packages: GitHub rejected workflow definition before any runner/job/step executed. GitHub annotation points to `.github/workflows/ci.yml` line 384 and `Unrecognized named-value: 'runner'`.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Root cause

В job `ai-bench-yandex-live` было:

```yaml
env:
  AI_BENCH_OUTPUT_DIR: ${{ runner.temp }}/ai-bench-yandex-live
```

Официальная GitHub context availability table разрешает для `jobs.<job_id>.env` только `github`, `needs`, `strategy`, `matrix`, `vars`, `secrets`, `inputs`. `runner` доступен уже внутри step-level contexts, но не в job-level `env`. Поэтому GitHub отклонял весь workflow до запуска `Python tests` и `AI-BENCH-001 package gate`.

GitHub Secrets `AI_BENCH_YANDEX_API_KEY` и `AI_BENCH_YANDEX_FOLDER_ID` не являются причиной этого failure: их значения не выводятся в код/логи, а run #201 остановлен до выполнения steps.

## 2. Stability correction r4

Исправлено:

```yaml
env:
  AI_BENCH_OUTPUT_DIR: /tmp/ai-bench-yandex-live
```

Дополнительно:

- `evals/VERSION` -> `1.1.3`;
- `scripts/check_ai_bench_package.py` выполняет dependency-free structural scan `.github/workflows/ci.yml`;
- package checker локально валидирует context roots внутри `jobs.<job_id>.env` и fail-closed отклоняет `runner/job/steps/env` там, где GitHub их не разрешает;
- `tests/test_ai_bench_package_layout.py` содержит positive test текущего workflow и negative regression fixture с `${{ runner.temp }}`;
- `.gitignore` снова исключает local/live benchmark runtime evidence, но package gate не зависит от hidden files;
- live job остаётся manual-only, default-off, зависит от `tests` и `ai-bench-001`, uses GitHub Secrets and uploads only sanitized evidence.

## 3. Regression evidence

Локально на exact updated tree подтверждены:

- AI-BENCH deterministic package gate: PASS;
- AI-BENCH unit discovery: 23 passed;
- targeted SYNC/SEARCH/package/hygiene regression: 41 passed;
- all 59 test modules executed in bounded groups: **301 passed, 14 environment-dependent skips, 8 subtests passed**;
- repository hygiene: PASS after generated-cache cleanup;
- document structure: PASS;
- Python compileall: PASS.

Fourteen skips are not promoted to PASS: they require Flask/Psycopg/PostgreSQL service conditions supplied by GitHub Actions. The external workflow remains authoritative for PostgreSQL integration, Docker build/smoke, encrypted restore and the complete route matrix.

## 4. Changed files

Functional/CI changes are limited to:

- `.github/workflows/ci.yml`;
- `.gitignore`;
- `evals/VERSION`;
- `evals/README.md`;
- `evals/artifacts/README.md`;
- `scripts/check_ai_bench_package.py`;
- `tests/test_ai_bench_package_layout.py`.

Canonical/repository docs are synchronized separately. No production module, dependency, migration or Render setting changed.

## 5. Security and isolation

- API key and Folder ID values remain only in GitHub Actions Secrets;
- no live AI request occurs on push or pull_request;
- manual live run is default-off;
- benchmark output is runner-local `/tmp/ai-bench-yandex-live`;
- production revision remains `20260819_0014`;
- `app.py`, routes, models, repositories, production services and migrations are unchanged.

## 6. Current gate

1. Upload stability hotfix r4.
2. Require green `Python tests` and `AI-BENCH-001 package gate`, including historical package steps.
3. Only after green ordinary CI run `Actions -> CI -> Run workflow -> run_ai_bench_live=true`.
4. Download sanitized artifact and complete the human writing-quality rubric.

## 7. Status decision

`AI-BENCH-001 stability hotfix r4` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS**.  
Previously completed packages remain **ВЫПОЛНЕНО** unless the rerun exposes a real regression.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.34 | 25.08.2026 | Live Yandex manual workflow candidate. |
| 1.4.35 | 25.08.2026 | Fixed calendar-dependent SYNC assertions and browser-upload dotfile dependency. |
| 1.4.36 | 25.08.2026 | Integrated manual live job into existing `ci.yml` after run #196 filename defect. |
| 1.4.37 | 26.08.2026 | Run #201 workflow parse defect fixed: removed illegal `runner` context from job-level env and added local context validation. |

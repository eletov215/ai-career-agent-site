# AI Career Agent — аудит источников v1.4.36

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.36 |
| Дата | 25 августа 2026 |
| Проверяемый пакет | AI-BENCH-001 stability hotfix r3 |
| Production revision | `20260819_0014` |
| Статус | НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальный source audit

Источником кода является предоставленный пользователем ZIP `ai-career-agent-site-eletov215-patch-1.zip`, экспортированный из GitHub после run `#196`. В нём подтверждена точная причина обоих CI failures: файл с live workflow содержимым существовал как `.github/workflows/ai-bench-live` без расширения, тогда как tests/package gate требовали `.github/workflows/ai-bench-live.yml`.

Сравнение с поставкой v1.4.35 показало: количество файлов одинаковое; единственная path-разница — потерянное расширение workflow; `.gitignore` не получил три строки artifact policy. Production Python, migrations, requirements и user routes совпадают.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Root cause

GitHub Actions исполняет workflow только из YAML-файлов в `.github/workflows`. Extensionless file не являлся workflow. Одновременно:

- `tests/test_ai_bench_package_layout.py` пытался прочитать отсутствующий `.yml` и падал `FileNotFoundError`;
- `scripts/check_ai_bench_package.py` считал тот же path обязательным и завершался до deterministic run.

Это один packaging/layout defect, а не два независимых functional regressions.

## 2. Stability correction

`evals 1.1.2` больше не требует отдельного live workflow filename:

- `workflow_dispatch` input `run_ai_bench_live` добавлен в существующий `.github/workflows/ci.yml`;
- job `ai-bench-yandex-live` встроен в тот же workflow;
- default input — `false`;
- job condition разрешает запуск только при manual dispatch и explicit `true`;
- `needs: tests, ai-bench-001` не позволяет обращаться к Yandex до успешного завершения всех исторических package gates;
- concurrency group предотвращает параллельные billable runs;
- secrets используются только через GitHub Actions Secrets;
- artifact upload использует `actions/upload-artifact@v7`;
- package gate и unit tests проверяют integrated contract.

Clean full archive удаляет extensionless stale file. Patch-only не зависит от его удаления: если он останется в GitHub, checker выдаст только warning, а executable job берётся из `ci.yml`.

## 3. Regression evidence

Локально подтверждены:

- AI-BENCH package gate: PASS;
- AI-BENCH unit tests: 20 passed;
- all available test modules in bounded groups: 298 passed;
- environment-dependent skips: 14 (Flask/Psycopg/PostgreSQL/Docker unavailable locally);
- search pagination: 20 passed;
- remaining source/sync/vacancy regression: 44 passed;
- core data/auth/profile/privacy/non-route regression: 140 passed, 2 skips;
- provider/repository/resume/search regression: 74 passed;
- repository hygiene: PASS after cleanup;
- document structure and YAML parse: PASS.

The external GitHub workflow remains authoritative for Flask route gates, PostgreSQL service integration, Docker build/smoke, encrypted PostgreSQL restore and the complete historical CI matrix.

## 4. Changed files

Functional/CI changes:

- `.github/workflows/ci.yml`;
- `.gitignore`;
- `evals/VERSION`;
- `scripts/check_ai_bench_package.py`;
- `tests/test_ai_bench_package_layout.py`.

Repository Markdown canonical documents were synchronized. Clean full package removes `.github/workflows/ai-bench-live`. No production module changed.

## 5. Security and isolation

- no API key or Folder ID value is committed;
- no live request occurs on push or pull request;
- manual live request is default-off and gated by all ordinary jobs;
- output remains in `${{ runner.temp }}` and only sanitized evidence is uploaded;
- no `app.py`, production route, model, repository, service, dependency or migration change;
- production revision remains `20260819_0014`.

## 6. Current gate

1. Upload hotfix r3.
2. Require green `Python tests` and `AI-BENCH-001 package gate`, including all historical steps.
3. Open `Actions -> CI -> Run workflow` and set `run_ai_bench_live=true`.
4. Download the sanitized artifact and complete the human rubric.

## 7. Status decision

`AI-BENCH-001 stability hotfix r3` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS**.  
Completed packages remain completed, subject to regression confirmation.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.32 | 24.08.2026 | Initial AI-BENCH implementation candidate. |
| 1.4.33 | 24.08.2026 | Scalar-leaf unsupported-number scorer hotfix. |
| 1.4.34 | 25.08.2026 | Live Yandex manual workflow candidate. |
| 1.4.35 | 25.08.2026 | Fixed calendar-dependent SYNC assertions and browser-upload dotfile dependency. |
| 1.4.36 | 25.08.2026 | Run #196 audited; eliminated separate workflow filename dependency by integrating manual live job into existing `ci.yml`. |

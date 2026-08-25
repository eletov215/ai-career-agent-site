# AI Career Agent — аудит источников v1.4.35

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.35 |
| Дата | 25 августа 2026 |
| Проверяемый пакет | AI-BENCH-001 stability hotfix r2 |
| Production revision | `20260819_0014` |
| Статус | НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальный source audit

GitHub run `#192` предоставил два точных failure trace. Оба локализованы в тестовом/package контуре и не подтверждают отказ production-функций.

1. SYNC-001: `TrudvsemSyncService.run_once()` завершился `succeeded`, `processed=3`, `saved=3`. Падение возникло только при последующей проверке через `VacancyStore.count()` с default `period_days=7` и фиксированным `published_at=2026-08-18T08:00:00Z`.
2. AI-BENCH: checker требовал два dotfile (`evals/.gitignore`, `evals/artifacts/.gitkeep`), отсутствовавших после GitHub browser upload. Unit-test contract уже ожидал browser-safe visible scaffold, поэтому package был внутренне несогласован.

Hotfix r2 устраняет обе причины, не меняя Flask, production services, dependencies, migrations или schema revision.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Источник истины

- База кода: live Yandex candidate v1.4.34, подготовленный поверх пользовательского GitHub `main` archive `(21)`.
- Фактическое состояние текущего GitHub upload подтверждено screenshots run `#192`.
- API secrets не передавались в исходники и остаются в GitHub Actions Secrets.

## 2. Root cause: SYNC-001

Test fixture публиковал все вакансии фиксированной датой 18 августа. Проверка durable cache использовала пользовательский search/count contract с семидневным recency filter. После наступления 25 августа записи перестали входить в выдачу, хотя source records были сохранены и worker lifecycle assertions прошли.

Исправление: тесты worker persistence теперь используют `source_status_counts("trudvsem")` и проверяют `active` source records. Пользовательский recency filter продолжает отдельно тестироваться в SEARCH packages.

## 3. Root cause: AI-BENCH package layout

GitHub browser folder upload не гарантировал перенос nested dotfiles. Функциональный gate не должен зависеть от таких файлов.

Исправление:

- добавлен visible `evals/artifacts/README.md`;
- `REQUIRED` больше не содержит dotfiles;
- существующий layout regression test подтверждает browser-upload-safe contract;
- package version поднята до `1.1.1`;
- root ignore policy содержит `evals/artifacts/*` с исключением visible README;
- live workflow пишет evidence в `${{ runner.temp }}`, поэтому repository checkout не используется как output directory.

## 4. Regression evidence

Локально подтверждены:

- all 59 test modules in four bounded chunks: **298 passed, 14 environment-dependent skips, 8 subtests passed**;
- `tests/test_sync_worker.py`: 9 passed;
- exact SYNC-001 available gate: 84 passed, 1 environment skip;
- exact SYNC-002 available gate: 92 passed;
- deterministic AI-BENCH package gate: PASS;
- AI-BENCH unittest discovery: 20 passed;
- SEARCH-001/002/003/004/005 available gates: PASS;
- AUTH-001/002, PROF-001/002/003, PRIV-001 available gates: PASS;
- SQLite migration chain through `20260819_0014`: PASS;
- Alembic check, infra manifest and document structure: PASS.

Local environment did not contain Flask, Psycopg or Docker and had no package-network access. Corresponding route, PostgreSQL service and container gates remain mandatory in GitHub Actions and are not declared locally passed.

## 5. Changed functional, CI and test files

- `.github/workflows/ai-bench-live.yml`;
- `.gitignore`;
- `evals/VERSION`;
- `evals/ai_bench/__init__.py`;
- `evals/ai_bench/providers.py`;
- `evals/config/yandex-live.json`;
- `evals/artifacts/README.md`;
- `scripts/check_ai_bench_package.py`;
- `scripts/check_document_structure.py`;
- `scripts/check_repository_hygiene.py`;
- `tests/test_ai_bench_package_layout.py`;
- `tests/test_ai_bench_providers.py`;
- `tests/test_document_structure.py`;
- `tests/test_repository_hygiene.py`;
- `tests/test_search_deduplication.py`;
- `tests/test_sync_incremental.py`;
- `tests/test_sync_worker.py`.

Repository Markdown documentation was synchronized separately. No production Python module changed.

## 6. Security and isolation

- no API key/folder ID value is committed;
- Yandex authorization documentation currently uses two scope names: the key-creation page lists `yc.ai.languageModels.execute` for Model Gallery text generation, while Completions guides reference `yc.ai.foundationModels.execute`; role `ai.languageModels.user` is confirmed, and the manual workflow preflight is the decisive external check because the repository cannot inspect key metadata stored in GitHub Secrets;
- no live request is made by ordinary CI;
- live workflow remains manual-only;
- no `app.py`, route, model, repository, production service, requirement or migration change;
- production revision remains `20260819_0014`.

## 7. Current gate

1. Upload hotfix r2.
2. Require green `Python tests` and `AI-BENCH-001 package gate` with all historical package steps.
3. Only after ordinary CI is green, manually run `AI-BENCH-001 Live Yandex`.
4. Download sanitized artifact and complete the human rubric.

## 8. Status decision

`AI-BENCH-001 stability hotfix r2` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS**.  
Completed packages remain completed, subject to regression confirmation.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 9. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.32 | 24.08.2026 | Initial AI-BENCH implementation candidate. |
| 1.4.33 | 24.08.2026 | Scalar-leaf unsupported-number scorer hotfix. |
| 1.4.34 | 25.08.2026 | Live Yandex manual workflow candidate. |
| 1.4.35 | 25.08.2026 | CI run #192 audited; fixed calendar-dependent SYNC assertions and browser-upload dotfile package dependency. |

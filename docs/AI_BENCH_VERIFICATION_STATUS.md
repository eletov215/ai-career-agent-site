# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.3 |
| Дата | 25 августа 2026 |
| Пакет | AI-BENCH-001 stability hotfix r2 |
| Статус | НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |
| Production revision | `20260819_0014` |

## 1. External failure evidence

GitHub run `#192` stopped in two independent places:

- `Verify SYNC-001 external worker controls`: two cache-count assertions returned zero even though the sync run itself reported `processed=3`, `saved=3`, `status=succeeded`;
- `AI-BENCH-001 package gate`: required files `evals/.gitignore` and `evals/artifacts/.gitkeep` were absent after browser upload.

## 2. SYNC test correction

The assertions were testing sync persistence through a time-filtered vacancy search with a fixed publication timestamp. They now assert persisted active source-record counts directly:

```text
source_status_counts("trudvsem") == {"active": 3}
source_status_counts("trudvsem") == {"active": 1}
```

This keeps SYNC worker tests independent from calendar date while preserving SEARCH recency-filter coverage in its own package. Related persistence-only assertions in `tests/test_sync_incremental.py` and `tests/test_search_deduplication.py` use `period_days=0`, so future calendar boundaries cannot invalidate unrelated durability/dedup checks.

## 3. Browser-upload-safe package contract

`evals 1.1.1`:

- requires visible `evals/artifacts/README.md` instead of nested dotfiles;
- keeps a regression test that rejects hidden required paths;
- retains deterministic reference validation, schemas, redaction and anti-hallucination gates;
- keeps live output outside the checkout in GitHub runner temporary storage.

The optional nested dotfiles are removed from the canonical full package; their absence can no longer fail CI.

## 4. Local verification

| Проверка | Результат |
|---|---|
| All 59 local test modules, four bounded chunks | 298 passed, 14 environment-dependent skips, 8 subtests passed |
| `tests/test_sync_worker.py` | 9 passed |
| SYNC-001 available focused gate | 84 passed, 1 environment skip |
| SYNC-002 focused gate | 92 passed |
| Deterministic AI-BENCH package gate | PASS |
| AI-BENCH unittest discovery | 20 passed |
| SEARCH-001..005 available regression gates | PASS |
| AUTH-001/002 available regression gates | PASS |
| PROF-001/002/003 and PRIV-001 available regression gates | PASS |
| SQLite migration `0001 -> 0014` and Alembic check | PASS |
| Repository hygiene after cleanup | PASS |
| Infra manifest/document structure | PASS |

Flask/Psycopg/Docker-dependent checks could not execute in the local container because those packages/services were unavailable and network installation was blocked. GitHub Actions remains the authoritative external gate for those checks.

## 5. Live Yandex boundary

The manual workflow, candidate models and GitHub Secrets remain unchanged. No live API call should be launched until ordinary CI is green. Secret values are not stored in Git.

Current Yandex AI Studio documentation is inconsistent about the execution-scope name: the API-key creation page lists `yc.ai.languageModels.execute` for Model Gallery text generation, while the Completions and structured-output guides reference `yc.ai.foundationModels.execute`. The service-account role `ai.languageModels.user` is confirmed, and the existing key was created with `yc.ai.languageModels.execute`. GitHub Secrets expose neither the key value nor its metadata back to the repository, so the workflow preflight is the decisive external check. If Yandex returns a permission error, recreate the key through AI Studio's **Create API key** flow, which assigns the current required scopes.

## 6. Status decision

**AI-BENCH-001 remains open.** Hotfix r2 is locally verified but requires a clean GitHub Actions run. After that, run the live comparative workflow and complete the manual rubric.

`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 7. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 24.08.2026 | Initial benchmark implementation candidate and external-run gate. |
| 1.1 | 24.08.2026 | Scalar-leaf numeric scorer correction prepared. |
| 1.2 | 25.08.2026 | Scorer hotfix CI green; Yandex live candidate prepared. |
| 1.3 | 25.08.2026 | Run #192 audited; fixed SYNC calendar dependency and browser-upload dotfile gate dependency; rerun required. |

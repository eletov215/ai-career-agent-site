# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.4 |
| Дата | 25 августа 2026 |
| Пакет | AI-BENCH-001 stability hotfix r3 |
| Статус | НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |
| Production revision | `20260819_0014` |

## 1. External failure evidence

GitHub run `#196` failed in two jobs with the same missing path:

```text
.github/workflows/ai-bench-live.yml
```

`Python tests` raised `FileNotFoundError` in `test_live_workflow_uses_node24_artifact_action`. The dedicated package gate reported the same path as a missing required file.

The uploaded ZIP contains the complete YAML content under:

```text
.github/workflows/ai-bench-live
```

Therefore the failure is a filename/upload-layout defect. It does not show a failure in SYNC, SEARCH, AUTH, PROF, PRIV or production runtime.

## 2. Architectural correction

The live job is moved into the already established `.github/workflows/ci.yml`:

```text
workflow_dispatch input: run_ai_bench_live (boolean, default false)
job: ai-bench-yandex-live
condition: manual dispatch + explicit true
needs: tests, ai-bench-001
concurrency: ai-bench-001-yandex-live
```

Consequences:

- no extra workflow file must survive browser upload;
- normal push/PR behavior remains unchanged;
- the first Yandex API request cannot occur until all previous package gates pass;
- users must explicitly opt into the billable live run;
- concurrent billable runs are not started.

## 3. Package contract

`evals 1.1.2` requires `.github/workflows/ci.yml`, not a newly added workflow file. The gate verifies the manual input, job condition, dependencies, secret references, timeout, concurrency and `actions/upload-artifact@v7`.

A legacy extensionless `.github/workflows/ai-bench-live` is ignored with a warning for patch compatibility. The clean full project removes it.

## 4. Local verification

| Проверка | Результат |
|---|---|
| Deterministic AI-BENCH package gate | PASS |
| AI-BENCH unittest discovery | 20 passed |
| Package-layout regression | PASS |
| Current CI YAML parse | PASS |
| Available project test matrix | 298 passed, 14 environment-dependent skips |
| Search pagination | 20 passed |
| Source/sync/vacancy regression | 44 passed |
| Core data/auth/profile/privacy regression | 140 passed, 2 skips |
| Provider/repository/resume/search regression | 74 passed |
| Repository hygiene | PASS |
| Document structure | PASS |

Local environment lacks Flask, Psycopg/PostgreSQL and Docker. Those gates are not declared locally passed and remain mandatory in GitHub Actions.

## 5. Production boundary

No changes were made to:

```text
app.py
config.py
routes/
models/
repositories/
production services
requirements.txt
migrations/
Render configuration
```

Production schema remains `20260819_0014`. No production AI route exists.

## 6. Next external gate

1. Upload hotfix r3.
2. Confirm the normal `CI` run is fully green.
3. Open `Actions -> CI -> Run workflow`.
4. Set `run_ai_bench_live=true`.
5. Review the artifact and complete the human rubric.

## 7. Status decision

**AI-BENCH-001 remains open.** Hotfix r3 is locally verified but requires clean GitHub Actions evidence and then the live comparative run.

`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 24.08.2026 | Initial benchmark implementation candidate and external-run gate. |
| 1.1 | 24.08.2026 | Scalar-leaf numeric scorer correction prepared. |
| 1.2 | 25.08.2026 | Scorer hotfix CI green; Yandex live candidate prepared. |
| 1.3 | 25.08.2026 | Fixed SYNC calendar dependency and browser-upload dotfile dependency. |
| 1.4 | 25.08.2026 | Run #196 audited; integrated live job into existing `ci.yml` to remove separate workflow filename dependency. |

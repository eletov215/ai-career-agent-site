# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.5 |
| Дата | 26 августа 2026 |
| Пакет | AI-BENCH-001 stability hotfix r4 |
| Статус | НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |
| Production revision | `20260819_0014` |

## 1. External failure evidence

GitHub run `#201` failed before jobs started. Annotation:

```text
Invalid workflow file: .github/workflows/ci.yml#L1
Line: 384, Col: 28
Unrecognized named-value: 'runner'
```

The referenced line was:

```yaml
AI_BENCH_OUTPUT_DIR: ${{ runner.temp }}/ai-bench-yandex-live
```

This is a workflow-definition error, not a failing application test. No `Python tests`, package gate, provider request or production route executed.

## 2. Verified rule

GitHub's context availability table for `jobs.<job_id>.env` allows `github`, `needs`, `strategy`, `matrix`, `vars`, `secrets`, `inputs`. It does not allow `runner`. The `runner` context is valid at step level after a runner exists.

## 3. Correction

Hotfix r4 changes the job-level output path to:

```yaml
AI_BENCH_OUTPUT_DIR: /tmp/ai-bench-yandex-live
```

`evals` is `1.1.3`. The package checker now parses the workflow and rejects unsupported context roots in job-level `env`. Regression tests prove a fixture with `${{ runner.temp }}` is rejected while the current workflow passes.

## 4. Local verification

- deterministic AI-BENCH package gate: PASS;
- AI-BENCH unit tests: 23 passed;
- targeted current-package/SYNC/SEARCH/hygiene regression: 41 passed;
- all repository test modules in bounded groups: 301 passed, 14 environment-dependent skips, 8 subtests;
- repository hygiene after cleanup: PASS;
- document structure: PASS;
- compileall: PASS.

## 5. Security

GitHub Secret values are not committed. The live benchmark remains manual-only and default-off. The output path is runner-local `/tmp`; sanitized evidence is uploaded only after an explicit live run. Production Flask code and database revision are unchanged.

## 6. Remaining external gate

1. Upload r4.
2. Ordinary GitHub CI must be fully green.
3. Then run `CI` manually with `run_ai_bench_live=true`.
4. Review sanitized artifact and fill the human rubric.

## 7. Status decision

`AI-BENCH-001` remains **НУЖНА ПРОВЕРКА** until those external gates are complete.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.2 | 25.08.2026 | Live Yandex candidate after green scorer hotfix. |
| 1.3 | 25.08.2026 | Stability r2 after run #192. |
| 1.4 | 25.08.2026 | Stability r3 after run #196 workflow filename defect. |
| 1.5 | 26.08.2026 | Stability r4 after run #201 invalid job-level `runner` context. |

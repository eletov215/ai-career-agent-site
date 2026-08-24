# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.1 |
| Дата | 24 августа 2026 |
| Пакет | AI-BENCH-001 hotfix r1 |
| Статус | НУЖНА ПРОВЕРКА GITHUB; LIVE COMPARATIVE RUN PENDING |
| Production revision | `20260819_0014` |

## 1. Initial CI result

Candidate v1.4.32 was rejected by GitHub Actions:

```text
Python tests: 3 failed, 390 passed
AI-BENCH-001 package gate: failed
vacancy-match-ru-01: unsupported_numbers [{path: '$', value: '78'}]
vacancy-match-en-01: unsupported_numbers [{path: '$', value: '72'}]
```

This rejection is accepted as valid evidence; v1.0 statements that the external GitHub gate had passed are superseded.

## 2. Root cause

The unsupported-number scorer inspected both JSON containers and scalar leaves. The root dictionary was stringified, so an allowed generated `$.match_score` was scanned again as if it were a claim at `$`.

## 3. Hotfix implementation

- skip container values in `_unsupported_numbers()`;
- continue checking all scalar leaves;
- keep `generated_numeric_paths` exemptions exact and bounded;
- test that reference `match_score` passes;
- test that a narrative `99 years` claim still fails at `$.recommendation`;
- preserve token counts, fingerprints and SHA-256 values while redacting real credentials.

## 4. Local verification

| Проверка | Результат |
|---|---|
| Python compile for benchmark files | PASS |
| AI-BENCH unittest discover | 11 tests PASS |
| Strict deterministic reference run | 8/8 PASS |
| Dedicated package gate | PASS |
| Forbidden claims | 0 |
| Unsupported numbers | 0 |
| Dataset/PII guard | PASS |
| Secret-redaction tests | PASS |
| Production route/migration isolation | PASS |

Evidence:

- `docs/evidence/ai-bench-001/validation.json`;
- `docs/evidence/ai-bench-001/reference-run.json`;
- `docs/evidence/ai-bench-001/reference-report.md`.

## 5. What remains unverified

- the full GitHub workflow after hotfix upload;
- live external model quality, latency, quota/error behavior and cost;
- manual writing-quality rubric;
- provider decision for AI-PROVIDER-001.

## 6. Status decision

**Hotfix r1 is ready for GitHub. AI-BENCH-001 is not marked complete.** A green GitHub rerun will close only the implementation/CI defect; the package still requires the approved live comparative run and manual review.

## 7. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 24.08.2026 | Initial implementation candidate and external-run gate defined. |
| 1.1 | 24.08.2026 | Recorded GitHub rejection, fixed root-container numeric false positive and metric over-redaction, added regressions and regenerated local evidence. |

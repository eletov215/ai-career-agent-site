# AI-BENCH-001 benchmark report

- Run ID: `[REDACTED]`
- Started: `2026-08-24T10:27:07Z`
- Finished: `2026-08-24T10:27:07Z`
- Dataset: `ai-career-agent-golden-v1` v1.0.0
- Dataset fingerprint: `[REDACTED]`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Adapter | Cases | Passed | Error rate | Quality | Schema | Grounding | p50 latency, ms | p95 latency, ms | Estimated cost, USD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | fixture | 8 | 8 | 0.000 | 1.000 | 1.000 | 1.000 | 0.03 | 0.05 | n/a |

## Case results

| Provider | Case | Task | Language | Result | Quality | Grounding | Forbidden claims | Unsupported numbers | Latency, ms |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | resume_analysis | ru | PASS | 1.000 | 1.000 | 0 | 0 | 0.03 |
| reference | resume-analysis-en-01 | resume_analysis | en | PASS | 1.000 | 1.000 | 0 | 0 | 0.03 |
| reference | vacancy-match-ru-01 | vacancy_match | ru | PASS | 1.000 | 1.000 | 0 | 0 | 0.03 |
| reference | vacancy-match-en-01 | vacancy_match | en | PASS | 1.000 | 1.000 | 0 | 0 | 0.03 |
| reference | cover-letter-ru-01 | cover_letter | ru | PASS | 1.000 | 1.000 | 0 | 0 | 0.06 |
| reference | cover-letter-en-01 | cover_letter | en | PASS | 1.000 | 1.000 | 0 | 0 | 0.02 |
| reference | interview-ru-01 | interview_questions | ru | PASS | 1.000 | 1.000 | 0 | 0 | 0.04 |
| reference | interview-en-01 | interview_questions | en | PASS | 1.000 | 1.000 | 0 | 0 | 0.03 |

## Quality-gate interpretation

- Schema compliance is machine-checked against the versioned JSON schemas in `evals/schemas/`.
- Grounding combines valid evidence references, required evidence recall, and fixture-specific grounding terms.
- Forbidden claims and unsupported numeric claims are hard safety gates in the CI configuration.
- Human writing-quality rubrics are recorded as pending; the runner never fabricates manual-review scores.

## Limitations

- The included dataset is synthetic and intentionally excludes production user PII.
- Human writing-quality rubrics remain pending until a named reviewer records scores.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

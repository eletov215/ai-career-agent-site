# AI-BENCH-001 benchmark report

- Run ID: `ai-bench-20260826T122859Z-46e01af2`
- Started: `2026-08-26T12:28:59Z`
- Finished: `2026-08-26T12:28:59Z`
- Dataset: `ai-career-agent-golden-v1` v1.1.0
- Dataset fingerprint: `962aa5559802e897501890c04848572d3e1afc3980e1d97f782b94af67210b99`
- Benchmark contract: `1.1`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Cases | Passed | Errors | Quality | Grounding | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 8 | 8 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0.04 | 0.05 | n/a |

## Case results

| Provider | Case | Result | Quality | Grounding | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | resume-analysis-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | vacancy-match-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 67 | 0.04 |
| reference | vacancy-match-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 71 | 0.04 |
| reference | cover-letter-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | cover-letter-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | interview-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.05 |
| reference | interview-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |

## Grounded-v2 contract interpretation

- Evidence identifiers must be exact raw IDs and stay out of user-facing text.
- Resume `facts_not_verified` and cover-letter `caveats` are structured objects with their own evidence references.
- Cover-letter candidate-fit paragraphs must cite candidate facts; unsupported impact claims are a hard gate.
- Vacancy requirements are classified exactly once by requirement ID. Duplicate, missing, contradictory, or weakly evidenced classifications are hard failures.
- Vacancy numeric match scores are derived deterministically from weighted requirement classifications; the LLM no longer authors a percentage.
- Interview numbers are accepted only when already supplied as source/scenario facts, preventing accidental candidate-achievement fabrication.
- Human writing-quality rubrics remain pending; the runner never fabricates manual-review scores.

## Limitations

- The included dataset is synthetic and intentionally excludes production user PII.
- Human writing-quality rubrics remain pending until a named reviewer records scores.
- Vacancy numeric match scores are derived deterministically from requirement classifications; models do not author the score field.
- Live run v2 uses the grounded-v2 output contract, so its quality scores are not directly comparable to the earlier grounded-v1 run.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

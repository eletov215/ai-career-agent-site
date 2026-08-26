# AI-BENCH-001 benchmark report

- Run ID: `ai-bench-20260826T134329Z-91f7fb7a`
- Started: `2026-08-26T13:43:29Z`
- Finished: `2026-08-26T13:43:29Z`
- Dataset: `ai-career-agent-golden-v1` v1.2.0
- Dataset fingerprint: `7aaf4b72f605a13483ca00c9be63c94928e2115c209d7c3f1f48c11f92238c2f`
- Benchmark contract: `1.2`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Cases | Passed | Errors | Retries | Quality | Grounding | Language | Scenario provenance | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 8 | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0.05 | 0.80 | n/a |

## Case results

| Provider | Case | Result | Quality | Grounding | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.15 |
| reference | resume-analysis-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.07 |
| reference | vacancy-match-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 67 | 0.12 |
| reference | vacancy-match-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 71 | 0.03 |
| reference | cover-letter-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | cover-letter-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | interview-ru-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 1.15 |
| reference | interview-en-01 | PASS | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |

## Grounded-v2 contract interpretation

- Evidence identifiers must be exact raw IDs and stay out of user-facing text.
- Resume `facts_not_verified` and cover-letter `caveats` are structured objects with their own evidence references.
- Cover-letter candidate-fit paragraphs must cite candidate facts; unsupported impact claims are a hard gate.
- Vacancy requirements are classified exactly once by requirement ID. Duplicate, missing, contradictory, or weakly evidenced classifications are hard failures.
- Vacancy numeric match scores are derived deterministically from weighted requirement classifications; the LLM no longer authors a percentage.
- Interview numbers are accepted only when already supplied as source/scenario facts, and any scenario number must cite its scenario fact in the same question.
- Percent formatting is Unicode-normalized, so 20%, 20 % and 20 % represent the same grounded number.
- RU/EN user-facing language consistency is a separate hard gate.
- Cover letters distinguish candidate_fit from vacancy-grounded motivation paragraphs.
- Live provider diagnostics record only safe envelope shape/status metadata; raw provider bodies and refusal text are never persisted.
- Human writing-quality rubrics remain pending; the runner never fabricates manual-review scores.

## Limitations

- The included dataset is synthetic and intentionally excludes production user PII.
- Human writing-quality rubrics remain pending until a named reviewer records scores.
- Vacancy numeric match scores are derived deterministically from requirement classifications; models do not author the score field.
- Live run v3 uses the grounded-v2.1 output/scoring contract, so quality scores are not directly comparable to grounded-v1 or grounded-v2 runs.
- Language consistency and scenario-number provenance are machine-gated before manual writing review.
- Live OpenAI-compatible adapters may perform at most one explicitly configured bounded retry; retry evidence is retained in safe diagnostics.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

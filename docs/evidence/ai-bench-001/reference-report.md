# AI-BENCH-001 benchmark report

- Run ID: `ai-bench-20260826T181603Z-9f7ae17b`
- Started: `2026-08-26T18:16:03Z`
- Finished: `2026-08-26T18:16:03Z`
- Dataset: `ai-career-agent-golden-v1` v1.3.0
- Dataset fingerprint: `1051e1c8de4e5e1df484ed1a66f933e592e998eb7fb0ef527bf3e4f8d5ce16d9`
- Benchmark contract: `1.3`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Cases | Passed | Errors | Retries | Quality | Grounding | Language | Scenario provenance | Marker cleanup | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 8 | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 1.000 | 0 | 0.03 | 0.04 | n/a |

## Case results

| Provider | Case | Result | Retries | Quality | Grounding | Language | Scenario | Marker cleanup | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | resume-analysis-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | vacancy-match-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | 67 | 0.03 |
| reference | vacancy-match-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | 71 | 0.03 |
| reference | cover-letter-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | cover-letter-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.02 |
| reference | interview-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | interview-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |

## Grounded-v2.2 contract interpretation

- Evidence identifiers must be exact raw IDs. Simple decorated markers such as `(s1)`/`[s1]` are removed by deterministic display normalization; serialized metadata labels remain hard failures.
- Resume `facts_not_verified` and cover-letter `caveats` are structured objects with their own evidence references.
- Cover-letter candidate-fit paragraphs must cite candidate facts; causal/outcome language is allowed only when a cited candidate fact explicitly contains the corresponding impact.
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
- Grounded-v2.2 adds deterministic marker cleanup and expanded impact-safety gates; its quality scores are not directly comparable to earlier contracts.
- Language consistency and scenario-number provenance are machine-gated before manual writing review.
- Live OpenAI-compatible adapters may perform at most one explicitly configured bounded retry; retry evidence is retained in safe diagnostics.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

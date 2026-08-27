# AI-BENCH-001 benchmark report

- Run ID: `ai-bench-20260827T104236Z-08fce3bb`
- Started: `2026-08-27T10:42:36Z`
- Finished: `2026-08-27T10:42:36Z`
- Dataset: `ai-career-agent-golden-v1` v1.3.2
- Dataset fingerprint: `c0d6946af29356f8e19abdb1178beac3428752f7985d33d78f2ab01b9edc7b2f`
- Benchmark contract: `1.4`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Cases | Passed | Errors | Retries | Quality | Grounding | Language | Scenario provenance | Scenario repairs | Marker cleanup | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 8 | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 1.000 | 0 | 0.03 | 0.08 | n/a |

## Case results

| Provider | Case | Result | Retries | Quality | Grounding | Language | Scenario | Scenario repairs | Marker cleanup | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | resume-analysis-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | vacancy-match-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | 67 | 0.03 |
| reference | vacancy-match-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | 71 | 0.10 |
| reference | cover-letter-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | cover-letter-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.02 |
| reference | interview-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | interview-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |

## Grounded-v2.3 contract interpretation

- Evidence identifiers must be exact raw IDs. Simple decorated markers such as `(s1)`/`[s1]` are removed by deterministic display normalization; serialized metadata labels remain hard failures.
- Resume `facts_not_verified` and cover-letter `caveats` are structured objects with their own evidence references.
- Cover-letter candidate-fit paragraphs must cite candidate facts; causal/outcome language is allowed only when a cited candidate fact explicitly contains the corresponding impact.
- Vacancy requirements are classified exactly once by requirement ID. Duplicate, missing, contradictory, or weakly evidenced classifications are hard failures.
- Vacancy numeric match scores are derived deterministically from weighted requirement classifications; the LLM no longer authors a percentage.
- Interview factual/scenario numbers are accepted only when grounded in source facts. A narrowly scoped answer-cardinality instruction such as 'give 2 examples' is treated as formatting rather than a factual claim.
- When an interview question uses an exact scenario number that maps to exactly one scenario fact, the machine layer may deterministically append that scenario ID to the structured `evidence_ids`. Repairs are audited and unresolved or ambiguous provenance remains a hard failure.
- Percent formatting is Unicode-normalized, so 20%, 20 % and 20 % represent the same grounded number.
- RU/EN user-facing language consistency is a separate hard gate.
- Cover letters distinguish candidate_fit from vacancy-grounded motivation paragraphs.
- Live provider diagnostics record only safe envelope shape/status metadata; raw provider bodies and refusal text are never persisted.
- Human writing-quality rubrics remain pending; the runner never fabricates manual-review scores.

## Limitations

- The included dataset is synthetic and intentionally excludes production user PII.
- Human writing-quality rubrics remain pending until a named reviewer records scores.
- Vacancy numeric match scores are derived deterministically from requirement classifications; models do not author the score field.
- Grounded-v2.3 adds deterministic marker cleanup, uniquely inferable scenario-evidence repair, and expanded impact-safety gates; its quality scores are not directly comparable to earlier contracts.
- Language consistency and unresolved scenario-number provenance are machine-gated before manual writing review; exact one-to-one scenario evidence repairs are recorded separately.
- Live OpenAI-compatible adapters may perform at most one explicitly configured bounded retry; retry evidence is retained in safe diagnostics.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

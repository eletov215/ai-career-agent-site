# AI-BENCH-001 benchmark report

- Run ID: `ai-bench-20260913T144143Z-da496e5e`
- Started: `2026-09-13T14:41:43Z`
- Finished: `2026-09-13T14:41:43Z`
- Dataset: `ai-career-agent-golden-v1` v1.3.5
- Dataset fingerprint: `126e3ea078b5d6456491056e6c055610012cb0e64fbdacc1a1dc9d09fccbf631`
- Benchmark contract: `1.4`
- Execution mode: `deterministic_reference`
- Quality gate: **PASSED**

## Provider summary

| Provider | Cases | Passed | Errors | Retries | Quality | Grounding | Language | Scenario provenance | Scenario repairs | Kind repairs | Marker cleanup | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 8 | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 1.000 | 0 | 0.04 | 0.04 | n/a |

## Case results

| Provider | Case | Result | Retries | Quality | Grounding | Language | Scenario | Scenario repairs | Kind repairs | Marker cleanup | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | resume-analysis-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | resume-analysis-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |
| reference | vacancy-match-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | 67 | 0.04 |
| reference | vacancy-match-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | 71 | 0.03 |
| reference | cover-letter-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | cover-letter-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | interview-ru-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.04 |
| reference | interview-en-01 | PASS | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0 | n/a | 0.03 |

## Grounded-v2.6 contract interpretation

- Evidence identifiers must be exact raw IDs. Simple decorated markers such as `(s1)`/`[s1]` are removed by deterministic display normalization; serialized metadata labels remain hard failures.
- Resume `facts_not_verified` and cover-letter `caveats` are structured machine/audit objects with their own evidence references; cover-letter caveats are omitted from the presentation copy.
- Cover-letter candidate-fit paragraphs must cite candidate facts; causal/outcome language is allowed only when a cited candidate fact explicitly contains the corresponding impact.
- Vacancy requirements are classified exactly once by requirement ID. Duplicate, missing, contradictory, or weakly evidenced classifications are hard failures.
- Vacancy numeric match scores are derived deterministically from weighted requirement classifications; the LLM no longer authors a percentage.
- Interview factual/scenario numbers are accepted only when grounded in source facts. A narrowly scoped answer-cardinality instruction such as 'give 2 examples' is treated as formatting rather than a factual claim.
- When an interview question uses an exact scenario number that maps to exactly one scenario fact, the machine layer may deterministically append that scenario ID to the structured `evidence_ids`. Repairs are audited and unresolved or ambiguous provenance remains a hard failure.
- Percent formatting is Unicode-normalized, so 20%, 20 % and 20 % represent the same grounded number.
- RU/EN user-facing language consistency is a separate hard gate.
- Cover letters distinguish candidate_fit from vacancy-grounded motivation paragraphs; unverified candidate gaps must remain internal caveats and may not be disclosed in visible paragraphs.
- Unicode hyphen/dash variants are normalized for lexical grounding only; evidence semantics are unchanged.
- Vacancy-only candidate_fit paragraphs are reclassified to motivation only for explicit future-intent/motivation wording, with an audit record; gap-bearing candidate evidence is never repaired into visible motivation.
- Live provider diagnostics record only safe envelope shape/status metadata; raw provider bodies and refusal text are never persisted.
- Human writing-quality rubrics remain pending; the runner never fabricates manual-review scores.

## Limitations

- The included dataset is synthetic and intentionally excludes production user PII.
- Human writing-quality rubrics remain pending until a named reviewer records scores.
- Vacancy numeric match scores are derived deterministically from requirement classifications; models do not author the score field.
- Grounded-v2.6 retains the prior evidence, numeric, impact, language, scenario and match hard gates, adds a first-person cover-letter presentation gate that keeps unverified candidate gaps internal, and tightens coaching/actionability prompts; its quality scores are not directly comparable to earlier contracts.
- Language consistency and unresolved scenario-number provenance are machine-gated before manual writing review; exact one-to-one scenario evidence repairs are recorded separately.
- Live OpenAI-compatible adapters may perform at most one explicitly configured bounded retry; retry evidence is retained in safe diagnostics.
- This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors.

## Decision status

No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001.

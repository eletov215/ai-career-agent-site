# AI-BENCH-001 live run #2 review

- GitHub artifact: `ai-bench-001-yandex-live-32972783843.zip`
- Benchmark run ID: `ai-bench-20260826T131651Z-b91a62e9`
- Date: 2026-08-26
- Dataset: `ai-career-agent-golden-v1` v1.1.0 / grounded-v2
- Synthetic benchmark data only; no production user data or credentials copied into this review.
- Decision: no provider selected; findings drive grounded-v2.1 hardening before live run #3.

## Machine summary

| Provider | Passed | Errors | Quality | Grounding | Clean text | p50 ms | p95 ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Alice AI LLM | 5/8 | 0 | 0.949870 | 0.973958 | 1.000000 | 5264.467 | 8806.369 | 0.045373764 |
| Alice AI LLM Flash | 4/8 | 0 | 0.964583 | 0.941667 | 0.875000 | 5611.735 | 14373.449 | 0.007062295 |
| YandexGPT Pro 5.1 | 3/8 | 1 | 0.948289 | 0.952381 | 0.714286 | 3712.729 | 4315.782 | 0.032622946 |

Scores above are grounded-v2 evidence and are not directly comparable to grounded-v1 or the future grounded-v2.1 run because machine gates changed.

## Findings encoded into grounded-v2.1

1. Percent formatting must normalize regular, non-breaking and narrow non-breaking spaces: `20%`, `20 %`, and `20 %` are the same grounded numeric fact.
2. A number from a `kind=scenario` fact must cite the matching `sN` evidence in the same interview question object; merely appearing anywhere in the prompt is insufficient provenance.
3. A number that is absent from canonical source facts remains unsupported. In the English interview case, `30 days` is unsupported even though `90 days` is an allowed scenario fact.
4. User-facing language is now an explicit RU/EN hard gate. The Flash Russian cover-letter response was written in English and must fail regardless of other scores.
5. Cover-letter schema now separates `motivation` from `candidate_fit`. Vacancy-only evidence is legitimate for `motivation`; `candidate_fit` still requires candidate evidence.
6. OpenAI-compatible diagnostics distinguish HTTP status, envelope JSON validity, choices/message/content presence, content type, refusal presence and finish reason without storing raw response bodies or refusal text.
7. Live transport permits at most one configured retry for HTTP 429/5xx, transport failures/timeouts, or malformed response envelopes. Retry count/reason remains visible in evidence. HTTP 4xx other than 429 and model refusals are not retried.
8. The YandexGPT Pro 5.1 `cover-letter-en-01` error from live run #2 was reported only as a generic unsupported envelope by evals 1.2.0; grounded-v2.1 adds enough safe shape diagnostics to distinguish the failure class in a future run.

## Provider direction after run #2

Alice AI LLM remains the leading primary candidate because both resume-analysis and vacancy-match pairs passed grounded-v2. Flash remains a possible lower-cost candidate for narrower tasks, but language/evidence consistency is not yet reliable. YandexGPT Pro 5.1 remains less stable in structured/user-facing output and produced one provider error. This is a benchmark observation only, not an AI-PROVIDER-001 decision.

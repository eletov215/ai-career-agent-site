# AI-BENCH-001 live run #1 review

- GitHub artifact/run reference: `32958938365`
- Contract: grounded-v1 (`benchmark_version=1.0`)
- Requests: 24 total, 0 provider transport errors
- Decision: no provider selected; evidence used to harden grounded-v2

| Provider | Strict pass | Quality | Grounding | p50 ms | p95 ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| Alice AI LLM | 4/8 | 0.952178 | 0.957259 | 5193.153 | 9444.269 | 0.047868023 |
| Alice AI LLM Flash | 2/8 | 0.950094 | 0.897536 | 3146.667 | 3919.065 | 0.006081147 |
| YandexGPT Pro 5.1 | 3/8 | 0.937723 | 0.859077 | 5738.538 | 7977.200 | 0.034518028 |

## Findings encoded as regressions

- unsupported candidate skill/recommendation (for example Kubernetes in a case where it was not source-backed);
- empty/incomplete unverified-fact reporting;
- invalid/decorated evidence IDs (`Alternatively`, `[c1]`, punctuation);
- evidence metadata leaked into user-facing cover letters;
- unsupported causal/impact expansion of candidate experience;
- inconsistent vacancy requirement classification and unreliable model-authored numeric score;
- false-positive old numeric gate for legitimate hypothetical interview scenarios.

The raw artifact remains external to Git. `evals/regressions/live-run-1.json` stores only synthetic, minimal failure patterns needed for deterministic regression tests. Grounded-v2 scores must not be compared numerically with these grounded-v1 scores as if the scoring contract were identical.

# AI-BENCH-001 Alice Final run #3 review

- Source artifact: `ai-bench-001-yandex-alice-final-33163009779.zip`
- Source run ID: `ai-bench-20260828T102540Z-bcf4c2ed`
- Source benchmark: `1.4`, dataset `1.3.3`, contract `grounded-v2.4`
- Provider: `yandex-alice-ai-llm`
- Transport: 8/8 calls completed, 0 provider errors, 0 retries
- Source machine result: 6/8 PASS
- Mean quality: 0.975
- Mean grounding: 1.000
- p50: 4796.74 ms
- p95: 11855.16 ms
- Estimated cost: USD 0.051498352

## 1. Confirmed failures

Two cases failed while schema, language, evidence IDs, vacancy-match consistency and transport remained clean.

`cover-letter-en-01` failed only the unsupported-impact gate. The model explicitly disclosed the experimentation gap, cited `c5` + `v3`, and then wrote a future-learning sentence: `I am eager to grow in this area`. The paragraph was labeled `candidate_fit`, so the lexical impact detector interpreted `grow` as unsupported `growth_increase`. This is a paragraph-kind/intent classification mismatch, not an invented candidate achievement. A verified-skill or real impact claim must remain a hard failure.

`interview-ru-01` failed only the unsupported-number gate. The phrase `Назовите 2–3 ресурса или подхода...` is a response-cardinality instruction. It does not assert candidate experience, duration, salary, percentage, achievement or scenario data. The existing narrow exception covered examples/options/steps/reasons but not resources/approaches.

## 2. Grounded-v2.5 correction

The correction remains narrow and auditable.

1. A `candidate_fit` paragraph may be reclassified to `motivation` when it has explicit future intent, at least one vacancy fact, and either no candidate facts or only explicit unverified-gap candidate facts that the paragraph itself discloses. Verified skills, achievements, mixed positive candidate evidence and unsupported impact are never repaired.
2. Interview response-cardinality detection additionally recognizes imperative counts of resources/approaches. Unsourced factual durations, percentages, salary, experience numbers and outcomes remain hard failures.
3. RU/EN prompts explicitly ask the model to use `motivation` for disclosed-gap future learning and to avoid new numeric counts for resources/approaches as well as examples/options/steps/reasons.
4. The previously misplaced Alice Final run #2 regression tests are moved back inside the unittest class so ordinary CI actually executes them.

## 3. Offline replay

The retained raw Alice Final run #3 responses were replayed through `grounded-v2.5` without a new provider call.

- original: 6/8 PASS;
- grounded-v2.5 replay: 8/8 PASS;
- scenario-provenance repairs: 3;
- motivation-kind repairs: 2 total across the retained run;
- unsupported numbers after normalization: 0;
- unsupported impact claims after normalization: 0.

Machine-readable evidence: `alice-final-run-3-grounded-v2.5-replay.json`.

This replay is regression evidence only. A fresh Alice-only live run is still required because updated prompt behavior cannot be validated from retained responses. A named human writing-quality rubric remains mandatory after an 8/8 live machine pass.

## 4. Production boundary

No production AI provider, route, model, database table or migration is introduced. The hotfix is limited to `evals/`, AI-BENCH tests/scripts/workflow labels, regression evidence and canonical documentation. Production revision remains `20260819_0014`.

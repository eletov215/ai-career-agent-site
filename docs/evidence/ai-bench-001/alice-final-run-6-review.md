# AI-BENCH-001 — Alice Final run #6 review

**Artifact:** `ai-bench-001-yandex-alice-final-34766480932.zip`  
**Run ID:** `ai-bench-20260913T154901Z-44d67112`  
**Observed contract:** benchmark `1.4`, dataset `1.3.5`, `grounded-v2.6`  
**Provider:** `yandex-alice-ai-llm`

## Result

- provider calls: 8/8 completed;
- provider errors: 0;
- retries: 0;
- machine pass: **7/8**;
- mean quality: `0.986458`;
- mean grounding: `0.989583`;
- user-facing cleanliness: `1.000`;
- unsupported impact claims: **3**;
- p50: `3550.43 ms`;
- p95: `5611.53 ms`;
- estimated cost: `USD 0.053826221`.

The only failing case is `cover-letter-en-01`. The existing hard scorer correctly rejected three inferred effects that were not present in candidate evidence:

1. Figma/design systems -> inferred `ensuring a cohesive visual language across products`;
2. qualitative interviews -> inferred decision/user-need/product-direction effects;
3. product/engineering collaboration -> inferred implementation/delivery effects.

The opening also contained an ungrounded historical-familiarity statement (`long admired how your team approaches product design`). It did not cause the 7/8 failure under grounded-v2.6, but it is not supported by source facts and is explicitly gated in grounded-v2.6.1.

## Root cause

This is a generation-discipline failure, not a transport, schema, evidence-ID, language, numeric or provider-availability failure. Grounded-v2.6 already told the model not to infer outcomes, but the English cover-letter prompt still allowed too much prose expansion around sparse noun-phrase facts.

## Grounded-v2.6.1 decision

The next candidate keeps every existing hard safety threshold and does **not** repair unsupported model output. It tightens only the English cover-letter generation contract:

- short atomic first-person restatements of verified candidate facts;
- no purpose/benefit/result tail unless explicitly present in cited candidate evidence;
- no invented context such as user needs, business goals, technical requirements, product direction, implementation quality, consistency or scalability;
- no invented prior familiarity with the employer/team;
- exact run #6 failure patterns are versioned as regressions.

A fresh Alice Final live run is required because the prompt changed. AI-BENCH-001 remains open until 8/8 machine PASS and the focused named human re-review complete.

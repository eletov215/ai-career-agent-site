# AI-BENCH-001 Alice Final run #5 - named human review

Date of live run / human review: 2026-08-28  
Reviewer: **Шекунов Д.С.**

## Source artifact

- Artifact: `ai-bench-001-yandex-alice-final-33168005097.zip`
- Run ID: `ai-bench-20260828T114615Z-5b0d7a99`
- Provider: `yandex-alice-ai-llm`
- Benchmark: `1.4`
- Dataset: `ai-career-agent-golden-v1` `1.3.4`
- Contract: `grounded-v2.5`
- Provider calls: **8/8 completed**
- Machine result: **8/8 PASS**
- Provider errors: **0**
- Retries: **0**
- Mean quality: `1.000`
- Mean grounding: `1.000`
- Language consistency: `1.000`
- Match consistency: `1.000`
- p50 latency: `3447.243 ms`
- p95 latency: `5500.041 ms`
- Estimated cost: `USD 0.0504295`
- All hard safety counters: `0`

This live run confirmed the machine/safety gate, including the grouped-marker sanitizer fix. The named human writing-quality gate was then performed on the presentation outputs.

## Human review

### 1. Resume analysis RU

Scores: **5 / 4 / 4 / 4**.

Reviewer note: recommendations are useful and generally acceptable, but they should be phrased a little more softly. The product should offer next-step options rather than sound directive.

Decision: **revision requested for tone only**.

### 2. Resume analysis EN

Scores: **5 / 5 / 5 / 5**.

Reviewer note: fully acceptable.

Decision: **accepted**.

### 3. Vacancy match RU

Scores: **5 / 5 / 4 / 3**.

Reviewer note: the final recommendation should explain that, if the user really has Docker experience but it is simply not confirmed/reflected in the profile or resume, confirming it would allow AI Career Agent to recalculate the match and the resulting match may increase. The model must not invent the new percentage itself.

Decision: **revision requested for actionable next step**.

### 4. Vacancy match EN

Reviewer note: acceptable as written; the explanation and next-step guidance are present. No explicit numeric score vector was supplied by the reviewer, so none is fabricated here.

Decision: **accepted**.

### 5. Cover letter RU

Scores: **3 / 4 / 4 / 4 / 3**.

Reviewer note: the letter surfaces negative/unverified aspects of the job seeker and reads partly like an AI report about a candidate. The final letter should create the impression that the person wrote it themselves. It should be first-person, focus on verified strengths and motivation, and must not advertise missing/unverified skills to the employer.

Decision: **revision required**.

### 6. Cover letter EN

Reviewer note: the same qualitative issue as case 5 applies. The visible letter should not highlight the applicant's missing/unverified experimentation experience. No explicit numeric score vector was supplied, so none is fabricated here.

Decision: **revision required**.

### 7. Interview RU

Reviewer note: fully acceptable. No explicit numeric score vector was supplied.

Decision: **accepted**.

### 8. Interview EN

Reviewer note: fully acceptable. No explicit numeric score vector was supplied.

Decision: **accepted**.

## Human gate decision

**REVISION REQUIRED.**

The machine gate remains valid for the source live run, but AI-BENCH-001 cannot close because writing-quality issues remain in cases 1, 3, 5 and 6.

## Grounded-v2.6 corrective scope

The next benchmark package is intentionally limited to the human-review findings:

1. RU resume recommendations use softer conditional coaching language.
2. RU/EN vacancy recommendations explain the safe profile/resume verification path and deterministic recalculation without inventing a future percentage.
3. Cover-letter caveats remain required machine/audit metadata but are removed from the presentation copy.
4. Visible cover-letter paragraphs may not cite/disclose explicit unverified candidate gaps and may not describe the writer as `candidate/applicant`; first-person voice is required at letter level.
5. The previous automatic repair that could move an unverified-gap paragraph into visible `motivation` is removed. Only vacancy-only future-intent paragraphs may be reclassified.
6. Production application routes, models, database schema and Render revision remain unchanged.

Because the prompts/visible-writing contract changes, a **fresh Alice Final live run is required** after ordinary CI. The follow-up human review should focus on cases 1, 3, 5 and 6 while preserving regressions for 2, 4, 7 and 8.

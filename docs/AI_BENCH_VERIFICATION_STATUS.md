# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.7 |
| Дата | 26 августа 2026 |
| Пакет | AI-BENCH-001 grounded-v2.1 hardening |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #3 + MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. Confirmed external evidence

Stability r4 and grounded-v2 ordinary CI were confirmed green on `main`. Live run #1 completed 24/24 calls with zero provider errors and drove grounded-v2. Live run #2 then completed the grounded-v2 benchmark; its sanitized artifact is `32972783843` (`run_id=ai-bench-20260826T131651Z-b91a62e9`).

Live run #2 machine summary:

| Provider | Passed | Errors | Quality | Grounding | Clean text | p50 ms | p95 ms | Cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Alice AI LLM | 5/8 | 0 | 0.949870 | 0.973958 | 1.000000 | 5264.467 | 8806.369 | 0.045373764 |
| Alice AI LLM Flash | 4/8 | 0 | 0.964583 | 0.941667 | 0.875000 | 5611.735 | 14373.449 | 0.007062295 |
| YandexGPT Pro 5.1 | 3/8 | 1 | 0.948289 | 0.952381 | 0.714286 | 3712.729 | 4315.782 | 0.032622946 |

Grounded-v2 quality values are historical evidence and are not directly comparable with grounded-v2.1 scores because the machine contract changed.

## 2. Live run #2 findings

The second artifact confirmed that deterministic vacancy scores work as intended and that grounded-v2 materially improved Alice resume-analysis and vacancy-match behavior. It also exposed four remaining benchmark/transport gaps:

1. `20%`, `20 %` and `20 %` were semantically identical source numbers but not normalized identically.
2. A model could use a valid scenario number without citing the corresponding `sN` evidence in the same interview question.
3. A Russian case could return English user-facing text without a dedicated language gate.
4. YandexGPT Pro produced one generic unsupported chat-completions envelope error; evals 1.2.0 could not safely distinguish `content=null`, refusal, missing choices, invalid JSON or another shape failure.

The English Alice cover-letter also showed a legitimate vacancy-grounded motivation paragraph that the old schema forced into `candidate_fit`. This was a schema limitation, not a candidate-fact hallucination.

## 3. Grounded-v2.1 implementation target

`evals 1.3.0` / benchmark `1.2` / dataset `1.2.0` must prove:

- Unicode-normalized numeric grounding for regular/NBSP/narrow-NBSP percent formatting;
- scenario-number provenance: a question using an `sN` number cites the same `sN` fact;
- unsourced numbers remain hard failures;
- explicit RU/EN user-facing language consistency;
- cover-letter `motivation` paragraphs may use vacancy evidence, while `candidate_fit` still requires candidate evidence;
- safe provider diagnostics: HTTP status, JSON validity, top-level shape, choices/message/content presence, content type, refusal presence and finish reason, with no raw body/refusal text persisted;
- at most one configured retry for 429/5xx, transport timeout/error or malformed envelope; HTTP 4xx except 429 and model refusals are not retried;
- retry count/reasons are visible in machine evidence;
- live-run #2 failure patterns are regression-tested;
- manual writing-quality scores remain pending and cannot override machine safety gates.

## 4. Local candidate evidence

- 50 AI-BENCH unit tests PASS, including new percent/language/scenario/motivation/retry/diagnostic regressions;
- deterministic grounded-v2.1 reference run: 8/8 PASS under strict gates;
- dataset fingerprint: `7aaf4b72f605a13483ca00c9be63c94928e2115c209d7c3f1f48c11f92238c2f`;
- full repository regression groups: 328 passed, 14 environment-dependent skips, 11 subtests passed, 0 confirmed failures;
- package gate, repository hygiene and document structure PASS after cache cleanup;
- production routes/models/services/dependencies/migrations remain unchanged; revision stays `20260819_0014`.

The 14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed.

## 5. Remaining external gate

1. Upload grounded-v2.1 candidate to `main` through the normal PR/CI path.
2. Require green `Python tests` and `AI-BENCH-001 package gate` with all historical package checks.
3. Run `Actions -> CI -> Run workflow -> run_ai_bench_live=true` on `main`.
4. Review sanitized live run #3 artifact, including retry/diagnostic evidence.
5. Complete the named human writing-quality rubric.
6. Record final benchmark decision; only then unblock `AI-PROVIDER-001`.

## 6. Status decision

`AI-BENCH-001` remains **НУЖНА ПРОВЕРКА**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.  
No production AI provider is connected.

## 7. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.5 | 26.08.2026 | Stability r4 fixed invalid job-level `runner` context. |
| 1.6 | 26.08.2026 | Green CI + live run #1 reviewed; grounded-v2 prepared for live run #2. |
| 1.7 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 adds Unicode numeric normalization, scenario provenance, language gate, motivation semantics, safe provider diagnostics and one bounded retry before live run #3. |

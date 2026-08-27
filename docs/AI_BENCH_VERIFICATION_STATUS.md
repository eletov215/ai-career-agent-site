# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.8 |
| Дата | 26 августа 2026 |
| Пакет | AI-BENCH-001 grounded-v2.2 final safety hardening |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #4 + MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. Confirmed external evidence

Grounded-v2.1 ordinary CI was confirmed green on `main`. Live run #3 then completed from artifact `32978362483` (`run_id=ai-bench-20260826T141439Z-b4d94c09`) with 24/24 provider calls, zero provider errors and zero retries.

Live run #3 machine summary under grounded-v2.1:

- **Alice AI LLM:** 7/8 passed; 0 errors; quality 0.971354; grounding 0.963542; clean text 0.875000; p50 6835.051 ms; p95 8408.902 ms; cost USD 0.045744254.
- **Alice AI LLM Flash:** 4/8 passed; 0 errors; quality 0.955208; grounding 0.989583; clean text 0.750000; p50 6964.514 ms; p95 12137.943 ms; cost USD 0.007288525.
- **YandexGPT Pro 5.1:** 5/8 passed; 0 errors; quality 0.963802; grounding 0.958333; clean text 0.750000; p50 2908.523 ms; p95 7410.318 ms; cost USD 0.039193435.

Those scores are historical evidence. Grounded-v2.2 changes the machine contract and is not directly score-comparable.

## 2. Live run #3 safety finding

Alice AI LLM remained the strongest overall candidate, but manual inspection found an unsupported-impact defect in a machine-passed Russian cover letter. The source stated documentation of typical solutions, SLA work and CRM usage. The generated text additionally claimed that those responsibilities accelerated repeat-request handling, organized accumulated experience and ensured stable service quality. Those outcome claims were absent from the cited candidate facts.

Alice `interview-ru-01` also showed the intended distinction between presentation noise and provenance: `(s1)`/`(s2)` appeared in visible text, while the `20%` follow-up omitted structured `s1` evidence. A presentation sanitizer may remove visible markers, but it must not cure the missing citation.

## 3. Grounded-v2.2 implementation target

`evals 1.4.0` / benchmark `1.3` / dataset `1.3.0` must prove:

- source-matched cover-letter impact families, with unsupported speed/time, efficiency, quality/reliability, growth, reduction and conversion/retention outcomes blocked;
- exact regression coverage for the live-run #3 Alice impact phrases;
- machine scoring on the untouched structured provider response;
- a separate presentation-safe copy that removes only simple decorated known evidence markers;
- hard failure for missing provenance, unknown evidence IDs, `evidence_ids:` labels and serialized schema/debug metadata;
- same-question scenario provenance remains mandatory after presentation repair;
- existing deterministic vacancy score, structured unverified/caveat, language, claim-evidence, safe diagnostics and bounded retry controls remain intact;
- manual writing-quality scores remain pending and cannot override machine safety gates.

## 4. Local candidate evidence

- 55 AI-BENCH unit tests PASS;
- deterministic grounded-v2.2 reference run: 8/8 PASS under strict gates;
- dataset fingerprint: `1051e1c8de4e5e1df484ed1a66f933e592e998eb7fb0ef527bf3e4f8d5ce16d9`;
- full repository regression groups: 333 passed, 14 environment-dependent skips, 12 subtests passed, 0 confirmed failures;
- package gate, repository hygiene, document structure and infra manifest PASS after generated-cache cleanup;
- SQLite migration chain `0001 -> 0014`, current/check `20260819_0014` PASS;
- production routes/models/services/dependencies/migrations remain unchanged; revision stays `20260819_0014`.

The 14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed.

## 5. Grounded-v2.2 replay of live run #3

The same raw live-run #3 responses were replayed locally under the new live thresholds. This is regression evidence only, not a new provider run:

- Alice AI LLM: 5/8; both cover-letter cases now fail unsupported-impact safety under the stricter contract, and Russian interview still fails grounding/scenario provenance; two simple decorated markers are repairable presentation noise.
- Alice AI LLM Flash: 4/8; blockers remain unverified-fact coverage, unsupported-impact safety and scenario provenance; 12 decorated markers are repairable but do not improve missing provenance.
- YandexGPT Pro 5.1: 4/8; hard serialized metadata, match consistency, caveat coverage and one unsupported-impact finding remain; four simple markers are repairable.

This replay confirms that the new impact gate catches the manual Alice safety finding without turning simple known marker decoration into a false hard failure.

## 6. Remaining external gate

1. Upload grounded-v2.2 candidate to `main` through the normal PR/CI path.
2. Require green `Python tests` and `AI-BENCH-001 package gate` with all historical package checks.
3. Run `Actions -> CI -> Run workflow -> run_ai_bench_live=true` on `main`.
4. Review sanitized final live run #4 artifact, including impact/scenario/repair evidence.
5. Complete the named human writing-quality rubric for the accepted candidate.
6. Record final benchmark decision; only then unblock `AI-PROVIDER-001`.

## 7. Status decision

`AI-BENCH-001` remains **НУЖНА ПРОВЕРКА**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.  
No production AI provider is connected.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.5 | 26.08.2026 | Stability r4 fixed invalid job-level `runner` context. |
| 1.6 | 26.08.2026 | Green CI + live run #1 reviewed; grounded-v2 prepared for live run #2. |
| 1.7 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 adds Unicode numeric normalization, scenario provenance, language gate, motivation semantics, safe provider diagnostics and one bounded retry before live run #3. |
| 1.8 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 adds source-matched impact-family safety, live-run-3 regressions and presentation-only simple marker repair before final live run #4. |

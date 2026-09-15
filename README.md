# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-14

| Поле | Значение |
|---|---|
| Current package | AI-001 - НУЖНА ПРОВЕРКА; synthetic-only technical foundation |
| Source code | Owner-supplied `main (31).zip`; documented closure overlay and AI-001 changes; remote GitHub not queried |
| Canonical versions | PLAN 1.5.0; PASSPORT 2.67; SOURCE_AUDIT 1.5.0 |
| Completed AI foundation | AI-BENCH-001 and AI-PROVIDER-001 - ВЫПОЛНЕНО; accepted evidence remains unchanged |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; operator, jurisdiction and launch countries not selected |
| Public AI / real data | Disabled in code; no generation POST route or real-data payload API |
| Technical candidate | Central policy, usage ledger, reservations, idempotency, Alice adapter, structured output, manual notice |
| Schema | Last verified staging: `20260819_0014`; candidate target: `20260914_0015` |
| Staging | Render web + clean Neon PostgreSQL; previous data not migrated |
| Verification | Local evidence only for AI-001; new ordinary GitHub CI, migration and staging smoke still required |
| Next action | Verify AI-001; then AI-002 technical development. LEGAL-001 must return before public AI/release |

Решение владельца: юридические вопросы отложены, но не отменены. Техническая разработка продолжается без передачи реальных резюме провайдеру.

<!-- ACA-CANONICAL-STATUS:END -->

## 1. Product and runtime

Career-support web service: account -> confirmed career profile -> resume -> real vacancy search -> future AI analysis/match/letters -> future tracker. Flask + Gunicorn (`app:app`), SQLAlchemy/Alembic PostgreSQL; external sync/privacy workers. Never create `app_fixed.py`.

## 2. Current work and checks

AI-001 is a synthetic-only technical candidate. AI-BENCH and AI-PROVIDER are complete; LEGAL-001 is deferred by the owner, not waived. No real-data generation endpoint exists. Keep deployment activation flags disabled.

```bash
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python scripts/check_ai001_package.py
python -m pytest -q tests/test_ai001_*.py
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Candidate schema is `20260914_0015`; last externally verified staging was `20260819_0014`. Ordinary CI and staging smoke are still required. Both paid benchmark workflow inputs remain false. No provider secret is needed for acceptance.

## 3. Source of truth and documentation

Use the most recently supplied GitHub archive for code and the latest canonical status for decisions. Source audit records the exact input hashes and all documentation drift. The user-facing document bundle and repository Markdown describe the same candidate.

Read `docs/AI_PROVIDER001_DECISION.md`, `docs/AI_PROVIDER001_COSTS.md`, `docs/AI_PROVIDER001_DATA_AND_FAILURE_POLICY.md`, `docs/AI_PROVIDER001_SOURCES.md` and `docs/AI_PROVIDER001_VERIFICATION_STATUS.md`.

## 4. Deployment and next package

Existing Render web uses clean Neon PostgreSQL staging at revision `20260819_0014`. No environment variables or schema changes are needed for this package. INFRA-001 remains the pre-release VPS field test. Actual data-location, backup, mail-delivery and production AI activation gates are not bypassed by healthy staging.

Owner strategy approval is recorded. After final green ordinary CI: LEGAL-001 -> AI-001. Do not enable production AI or change billing settings as part of this patch.

## 5. Upload and security

Apply PATCH contents over a clean synchronized repository; never delete the repository first. Keep `.git` intact. Do not commit keys, `.env`, databases, dumps, virtualenvs, caches, bytecode or raw production payloads. Full ZIP is a complete source snapshot; PATCH contains only changed/new paths.

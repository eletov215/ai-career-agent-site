# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-14

| Поле | Значение |
|---|---|
| Current package | AI-PROVIDER-001 - НУЖНА ПРОВЕРКА |
| Source code | Latest uploaded GitHub snapshot `ai-career-agent-site-main (30).zip`; 407 files |
| Canonical versions | PLAN 1.4.49; PASSPORT 2.63; SOURCE_AUDIT 1.4.49; AI-BENCH verification 1.16; provider ADR 1.0 |
| AI-BENCH-001 | ВЫПОЛНЕНО; accepted artifact `34830877796`, eight cases PASS and named human acceptance |
| Provider decision | Alice primary; manual reserve without generation; proposed limits/data policy; owner approval pending |
| Production AI | Not implemented or activated; policy JSON is an offline specification |
| Staging | Render web + clean Neon PostgreSQL (Oregon); previous readiness/site/search smoke confirmed |
| Database schema | `20260819_0014`; unchanged |
| Current verification | Local results in AI_PROVIDER001_VERIFICATION_STATUS; new external CI not yet run |
| Next package | LEGAL-001 after owner strategy approval and ordinary CI; AI-001 remains later |

The supplied canonical 1.4.48/2.62/1.16 files are authentic current inputs, but repository docs still contained the pre-closure status. This release reconciles them explicitly. Older dated evidence below remains historical and is not today's gate. No benchmark rerun or Render secret change is required for this architecture-only package.

<!-- ACA-CANONICAL-STATUS:END -->

## 1. Product and runtime

Career-support web service: account -> confirmed career profile -> resume -> real vacancy search -> future AI analysis/match/letters -> future tracker. Flask + Gunicorn (`app:app`), SQLAlchemy/Alembic PostgreSQL; external sync/privacy workers. Never create `app_fixed.py`.

## 2. Current work and checks

AI-BENCH-001 is complete on synthetic grounded-v2.6.1 / dataset 1.3.6 / evals 1.6.1. AI-PROVIDER-001 is an offline architecture candidate; the application still has no production AI provider.

```bash
python scripts/check_ai_provider_package.py
python -m unittest discover -s tests -p 'test_ai_provider*.py' -v
python scripts/check_ai_bench_package.py
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Ordinary CI does not make paid calls. Keep both live benchmark inputs false for this package. Updating an offline policy file does not enforce budgets or no-logging at runtime.

## 3. Source of truth and documentation

Use the most recently supplied GitHub archive for code and the latest canonical status for decisions. Source audit records the exact input hashes and all documentation drift. The user-facing document bundle and repository Markdown describe the same candidate.

Read `docs/AI_PROVIDER001_DECISION.md`, `docs/AI_PROVIDER001_COSTS.md`, `docs/AI_PROVIDER001_DATA_AND_FAILURE_POLICY.md`, `docs/AI_PROVIDER001_SOURCES.md` and `docs/AI_PROVIDER001_VERIFICATION_STATUS.md`.

## 4. Deployment and next package

Existing Render web uses clean Neon PostgreSQL staging at revision `20260819_0014`. No environment variables or schema changes are needed for this package. INFRA-001 remains the pre-release VPS field test. Actual data-location, backup, mail-delivery and production AI activation gates are not bypassed by healthy staging.

After owner strategy approval and green ordinary CI: LEGAL-001 -> AI-001. Do not enable production AI or change billing settings as part of this patch.

## 5. Upload and security

Apply PATCH contents over a clean synchronized repository; never delete the repository first. Keep `.git` intact. Do not commit keys, `.env`, databases, dumps, virtualenvs, caches, bytecode or raw production payloads. Full ZIP is a complete source snapshot; PATCH contains only changed/new paths.

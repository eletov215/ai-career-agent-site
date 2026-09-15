# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-15

| Поле | Значение |
|---|---|
| Current package | AI-002 - НУЖНА ПРОВЕРКА; rebuilt synthetic analysis/report candidate r2 |
| Source code | Owner main (32).zip; bc177dd6b970750f556f48f34dbd022a30e80a34; SHA-256 161d52efebf1762a5dd73f0be890b7afb204d2a26e34f9237341eaf832075de9 |
| Canonical versions | PLAN 1.5.2; PASSPORT 2.69; SOURCE_AUDIT 1.5.2 |
| Completed AI foundation | AI-BENCH-001 / AI-PROVIDER-001 / AI-001 - ВЫПОЛНЕНО in their accepted scope |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; public real-data AI and payments remain disabled |
| Schema | Staging verified 20260914_0015; candidate target 20260915_0016; three additive report/review tables |
| Candidate boundary | Two pinned resume fixtures; internal provider validation; private reference-only UI; no live dispatch from browser |
| Verification | New local measurements only; GitHub CI and Neon migration/smoke pending |
| Next action | Verify AI-002; preserve backup and closed AI switches; do not begin AI-003 yet |

<!-- ACA-CANONICAL-STATUS:END -->

## 0. AI-002 rebuilt candidate / 2026-09-15

Current: AI-002 v1.5.2 rebuild-r2, NEEDS_VERIFICATION. Baseline main (32) / bc177dd; schema target 0016. Read docs/AI002_RUNBOOK.md before applying. Public AI remains disabled. The optional /ai-analysis admin review uses pinned reference text, not live Alice. Canonical repository versions: PLAN1.5.2 / PASSPORT2.69.

## 1. Product and runtime

Career-support web service: account -> confirmed career profile -> resume -> real vacancy search -> future AI analysis/match/letters -> future tracker. Flask + Gunicorn (`app:app`), SQLAlchemy/Alembic PostgreSQL; external sync/privacy workers. Never create `app_fixed.py`.

## 2. Current work and checks

AI-001 is accepted as a synthetic-only technical foundation. AI-002 is the current rebuilt candidate awaiting external verification. AI-BENCH and AI-PROVIDER are complete; LEGAL-001 is deferred by the owner, not waived. No real-data generation endpoint exists. Keep deployment activation flags disabled.

```bash
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python scripts/check_ai001_package.py
python scripts/check_ai002_package.py
python -m pytest -q tests/test_ai001_*.py tests/test_ai002_*.py
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Candidate schema is `20260915_0016`; last externally verified staging is `20260914_0015`. Ordinary CI and staging smoke are still required. Both paid benchmark workflow inputs remain false. No provider secret is needed for acceptance.

## 3. Source of truth and documentation

Use the most recently supplied GitHub archive for code and the latest canonical status for decisions. Source audit records the exact input hashes and all documentation drift. This delivery contains a PATCH and updated repository Markdown. Previously delivered external canonical v1.5.1 documents remain the historical AI-001 acceptance evidence; no newly rendered external PDF/DOCX bundle is claimed for this PATCH-only rebuild.

Read `docs/AI_PROVIDER001_DECISION.md`, `docs/AI_PROVIDER001_COSTS.md`, `docs/AI_PROVIDER001_DATA_AND_FAILURE_POLICY.md`, `docs/AI_PROVIDER001_SOURCES.md` and `docs/AI_PROVIDER001_VERIFICATION_STATUS.md`.

## 4. Deployment and next package

Existing Render web uses Neon PostgreSQL staging, verified at revision `20260914_0015`. Back up before deployment: this package adds three report/review tables at `20260915_0016`. No provider credentials or activation changes are needed. INFRA-001 remains the pre-release VPS field test. Actual data-location, backup, mail-delivery and production AI activation gates are not bypassed by healthy staging.

Owner strategy approval and AI-001 acceptance are recorded. Next: AI-002 ordinary CI, migration and private review smoke. AI-003 remains planned. LEGAL-001 remains deferred but mandatory before public real-data AI or a commercial release. Do not enable production AI or change billing settings as part of this patch.

## 5. Upload and security

Apply PATCH contents over a clean synchronized repository; never delete the repository first. Keep `.git` intact. Do not commit keys, `.env`, databases, dumps, virtualenvs, caches, bytecode or raw production payloads. Full ZIP is a complete source snapshot; PATCH contains only changed/new paths.

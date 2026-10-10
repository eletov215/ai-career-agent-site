# AI004-M04-B — guarded schema successor proposal (review only)

**Status:** `PROPOSED / NOT APPROVED / NOT RELEASED`.  
**Repository baseline:** `main f4eb6aed7dcdfb07807b23fcb3928356a1fffb81` (merged PR #97 and #99).  
**Candidate:** [PR #98](https://github.com/eletov215/ai-career-agent-site/pull/98), `feature/ai004-m04b-persistent-cache`, **Draft / DO NOT MERGE**.  
**Schema:** `20261002_0023 -> 20261009_0024`, one additive Alembic head.  
**Owner authorization:** isolated code/test PR only. Protected historical guards, accepted evidence and production release require a *separate explicit approval*. This file does not create evidence or authorize any schema change.

## 1. Verified compatibility facts

1. PR #97 adds HOST-001 offline Alembic one-head gate and exact checkout pin. PR #99 extends the gate with `MATCHING_TABLES = {user_match_reports, user_match_cache}`, requiring BOTH entries in backup inventory AND in Stage C fixture's static `_schema_report.selected_tables` allowlist whenever a migration creates them.
2. M04B already adds both tables to `operations/backup.py._INVENTORY_TABLES` but **has not changed** accepted `scripts/host001_stage_c_fixture.py`. The merged HOST gate currently fails closed with: `Stage C schema digest omits M04B matching tables; review synthetic restore coverage.`
3. `database.CURRENT_REVISION = 20261009_0024` correctly matches M04B's new Alembic head. This is required by HOST and the app's health and upgrade routines. It conflicts with old package/check tests that pin `20261002_0023`.
4. Protected packages (including JOB-002/JOB-003/JOB-004, earlier AI/LEGAL) store accepted predecessor SHA256 for e.g. `database.py`, `models/__init__.py`, `operations/backup.py`, privacy modules. The old guards intentionally fail on changes without a pinned, reviewed **successor**. Do not rewrite predecessor hashes in place.
5. Render's `autoDeployTrigger: checksPass` and application startup migration `python scripts/manage_db.py upgrade` make a premature merge a potential **production Neon migration**. Green isolated QA is NOT deployment permission.

## 2. Required successor transition (separately approved; not implemented yet)

**A. Versioned evidence — append, do not rewrite history**

Prepare a new **AI004-M04B successor** manifest under `docs/evidence/ai-004/m04b-successor/` only after independent approval. Its verified, immutable fields must include:
- reviewed 40-char base/source SHA and tree SHA, package key, exact scope and changed-path allowlist;
- `schema_from=20261002_0023`, `schema_to=20261009_0024`, migration `down_revision=20261002_0023`, no fork, no backfill of accepted records;
- for every protected changed path, previous **SHA-256** from accepted chain and exact proposed current **SHA-256**; new files pinned separately;
- `legal_state=DRAFT`, `REAL_DATA_SUPPORTED=False`, `provider_calls=0`, `production_migration=NOT_RUN`, `deploy=NOT_RUN`;
- named SQLite and **disposable PostgreSQL 18** test run URLs, results and limitations; exact protected package baselines maintained.

No historical evidence file is edited to claim that its past schema was 0024.

**B. Explicit successor-chain registration with fail-closed guards**

A separate, owner-approved change must teach the existing **protected** validators to recognize precisely this new manifest and no arbitrary future revision. Review the complete transitive guard chain, including AI-001/002/003/004/005 and provider/LEGAL plus JOB-001/002/003/004, before naming touched files. Guarded source files (including their **own** checksums) require a reviewed bootstrap transition; blindly updating hashes or accepting arbitrary `CURRENT_REVISION` breaks evidence provenance.

Acceptance rule: no successor evidence -> historical `0023` and its checksums remain expected; exact reviewed signed/pinned successor evidence -> accept only `0024` and exact declared old-to-new SHA-256 transitions. A tampered manifest, missing protected path, unknown schema head or unexpected changed file MUST still fail. Prefer a dedicated guard package with table-driven unit tests and negative tamper cases.

**C. Historical migration-test chronology**

Do not remove assertions that the **accepted 0023** migration is correct. Make chronology explicit: test `upgrade_database(..., '20261002_0023')` and assert its state, then separately verify the approved `0023 -> 0024` transition. Known currently pinned checks: `tests/test_priv001_migration.py:33`, `tests/test_legal001_postgresql.py:162`, and package validators. Their source changes are protected; not undertaken without approval.

**D. HOST-001 Stage C schema/data/restore**

With HOST owners' agreement, update the fixed `selected_tables` in `scripts/host001_stage_c_fixture.py::_schema_report` to include both tables and verify their required constraints/indexes/FKs. This necessarily changes the accepted Stage C schema digest on 0024. Only claim `SCHEMA_INVENTORY_ONLY` for this static gate; do **not** relabel it as populated data recovery.

Keep a second suite on *disposable* PostgreSQL 18 that seeds two different synthetic owners, matching snapshots, versions, validated reports and signed cache claims, then exercises encrypted pg_dump/pg_restore to another disposable DB. After restore check row contents and HMAC, cross-account isolation, privacy ZIP, user/source FK cascades and tamper rejection. A Stage C runtime/remote Yandex recovery claim remains **NOT_RUN**; its manual apply workflow currently does not enforce this offline revision gate and must not be invoked.

**E. Rollout and rollback decision — a separate, later permission**

Only after (A–D) CI green, all canonical checks green, reviewed exact main SHA and independent approval: agree on production backup/recovery point, migration window, Render auto-deploy/startup handling, risk of automatic Neon upgrade and backward compatibility. Since downgrade drops new matching history/cache, require verified data preservation before any downgrade. No automatic deployment/migration is authorized by this proposal.

## 3. Already allowed in this Draft PR

- Add isolated, additive `0024` migration and M04B repository/model/privacy/backup code; test only on disposable SQLite/PostgreSQL.
- Merge current `main` *into feature branch only* to preserve PR #97/#99, without merging the PR itself.
- Add synthetic SQLite and PG18 encrypted backup/restore tests and negative tenant/HMAC/cascade tests in separate files/workflow.
- Record CI failures and generate review-only successor checklist.

## 4. Stop conditions

No protected gate/evidence or Stage C fixture rewrite without separate owner approval. No `main` merge, Neon/Render deployment, production backup/restore, Terraform apply/destroy, Yandex Cloud resources, provider dispatch, legal release or real data. Red generic CI remains a **release blocker**, never converted to green by disabling a check.

## 5. Approval requested

`Разрешаю отдельную разработку AI004-M04B successor-перехода 0023->0024: подготовку нового версионированного evidence, ограниченные изменения защищённых package guards/исторических тестов и HOST-001 Stage C fixture для статической схемы и синтетического restore, ТОЛЬКО в Draft PR/изолированном CI; merge, Render deploy, Neon migration и Yandex apply по-прежнему запрещены.`

This approval, if granted, authorizes reviewable **code changes only**, not automatic merging or applying the new schema.

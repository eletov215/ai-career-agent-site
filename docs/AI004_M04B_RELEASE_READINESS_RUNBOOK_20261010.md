# AI004-M04B — controlled 0023 → 0024 release readiness (NOT EXECUTED)

**Candidate:** Draft PR #98 in `eletov215/ai-career-agent-site`.  
**Reviewed base:** `a0166cdcb9087b3e5525ad6748e23d5ec0604913`.  
**Scope:** additive PostgreSQL matching-cache schema, owner-scoped synthetic repository, authenticated privacy export, backup inventory and exact successor CI.  
**Status:** PREPARED ONLY; no merge, production deployment, Neon migration, Terraform apply, billable AI calls, real-data matching or legal activation is authorized merely by this document.

## Two independent gates

1. **Code merge-ready:** full GitHub CI (including ordinary Python, LEGAL, JOB, matching PG18, protected package SHA) green on a frozen commit, `HOST-001 offline CI` passes in both PR and future main on a *verified privileged Stage C refusal*. Review negative tests and independent sign-off.
2. **Production GO:** explicit, separate owner-approved maintenance/deploy window, verified Neon restore and offsite encrypted `0023` backup, Render automation freeze, operator attendance, rollback resources and success metrics. Merge-ready does **not** imply production GO.

**HOST-001 separation:** `scripts/host001_stage_c_apply_gate.py` and `.github/workflows/host001-stage-c-apply.yml` MUST remain byte-locked to accepted `20261002_0023`; paid Stage C `0024` is **DENIED** pending a separate owner-reviewed field acceptance. A successful CI assertion of that denial is NOT permission for Stage C or Terraform. The second Stage C apply failed; the independent teardown succeeded and reported zero remote-state managed resources. Do not retest paid Yandex as part of M04B.

## Read-only infrastructure inventory at review time (2026-10-10)

- Neon project `ai-career-agent` (project id `odd-cherry-32789626`), PostgreSQL 18; default root branch `production` (`br-ancient-mountain-arql2jku`), production `public.alembic_version=20261002_0023` observed by a read-only SQL query.
- Neon history retention: **21,600 seconds (6 hours)**. **No snapshots** and no automatic snapshot schedule were listed during review; production branch was **not protected**. These are observations, not a recovery drill. Reconfirm immediately before the maintenance window. Do not treat 6h PITR as an offsite backup.
- Repository `render.yaml`: `autoDeployTrigger: checksPass`; `startCommand: python scripts/manage_db.py upgrade && python scripts/start_runtime.py`; readiness rejects revision mismatch. The actual Render service settings, rollback deploy/version and operator-controlled deployment freeze require direct verification in the chosen workspace; repository configuration alone is not proof of current Render state.

## Production release STOP / GO checklist (for a separately authorized operator)

**STOP unless every item is explicitly verified and timestamped (UTC):**

1. Freeze exact proposed merge SHA, `main` SHA, successor manifest digest and green checks. Confirm the privileged HOST apply preflight still refuses `0024` and the unprivileged CI verifies this refusal on **push main**, not just Draft PR.
2. Verify Neon *actual production target* and credentials out of logs: PostgreSQL major 18, root `production`, `alembic_version=20261002_0023`, single Alembic head and expected historical table inventory. Confirm no concurrent migration or stale locks. Only read schema/metadata before explicit migration permission.
3. In the owner-confirmed Render workspace check which service/branch `DATABASE_URL` points at without exposing the URL, the actual auto-deploy state, existing production SHA and currently healthy `/health/ready`. **Before merge** disable/hold auto deploy using separately approved operational settings and verify that it will not run the database upgrade on a GitHub check transition. `checksPass` must not be treated as a safety interlock.
4. Announce controlled maintenance, drain/make writes quiescent and stop background writers; measure existing row counts and backup timestamp. Create a full **AES-256-GCM encrypted** `pg_dump` to a private directory with `0600` staging/manifest, key escrow separate from dump. Preserve the runtime `FLASK_SECRET_KEY`: matching result HMAC is not recoverable if the key is lost/rotated. Never print `DATABASE_URL`, passwords, encryption keys or real resume/vacancy records in CI or the issue.
5. Validate backup file, manifest SHA, schema revision and table counts, then **restore to a private isolated recovery database**; verify source owner isolation, FK/CASCADE, key-based HMAC, privacy export, current critical user data and database revision. Restrict/erase any recovery copy containing real data per privacy requirements. A test restoring synthetic PG18 data on GitHub Actions does not substitute for proving this specific production backup. If rollback target is Neon, confirm available branch/snapshot/PITR method and permissions and its exact recovery point, without overwriting the primary during rehearsal.
6. Set realistic maximum downtime, RTO/RPO and monitor/operator coverage; have an approved backup-to-`0023` recovery procedure and known-good prior Render build ready. Get the **separate explicit owner's GO to merge/deploy/migrate** once these gates are evidenced.

**Only after GO**, in a single coordinated release window: merge the exact reviewed PR and start **one** explicitly coordinated code+database rollout, keeping concurrent auto-deploy/worker writers suppressed until migration is verified. Do not click merge while `startCommand` might run unsupervised.

## Verification after authorized schema upgrade

- Assert Neon `alembic_version=20261009_0024`, original historical table counts unchanged, exactly `user_match_reports` and `user_match_cache` added with required named UNIQUE/FK/CHECK/INDEX, and no orphaned new rows (should be empty until gated future matching work).
- Assert `/health/live` and `/health/ready` 200, DB pool OK, production Render SHA matches frozen release, no repeated upgrade failure or background-worker crash.
- Verify owner login/read-only existing resume, saved vacancies, privacy/account flows under explicitly approved synthetic QA accounts; do not send applications or invoke paid AI. `REAL_DATA_SUPPORTED=False`, `LEGAL-001=DRAFT`, matching route admission NOT enabled.
- Confirm external HOST-001 manual Stage C apply for `0024` remains blocked; monitor errors/latency and controlled background workers for the agreed observation window.
- Record exact UTC times, SHA, revision, protected backup/restore evidence, deviations, responsible operator and user GO/STOP decision.

## STOP and rollback (never downgrade matching tables as the default)

**STOP:** unexpected migration SQL failure, any schema mismatch, readiness 503, wrong target DB, lost owner/privacy integrity, invalid HMAC, unintended AI/provider calls, or failure to verify the backup/restore path.

1. Freeze traffic/writes/deployments. Keep incident evidence secret-free. Do **not** simply switch Render to code `0023` with DB `0024`: old `/health/ready` will reject it.
2. Do **not** use `alembic downgrade 20261002_0023` on live DB: migration `0024` drops **both** new tables and any reports/cache rows.
3. Restore **the coordinated pair**: production DB to the verified pre-0024 point using approved Neon PITR/snapshot or full offsite backup + Render to the previous exact code SHA. This may lose all writes after the chosen recovery point (RPO); notify affected users as required.
4. Validate restored `0023` revision, row counts, FK and account isolation, `/health/ready=200`, background workers and privacy functionality before reopening writes. Preserve and audit post-incident backups securely.
5. Require a new review and explicit owner authorization for any second attempt.

## Known limitations outside M04B

- No real-data matching, provider or M05/M06 integration; all current reports are synthetically generated.
- No successful paid HOST Stage C field test for `0024`; do not amend accepted Stage C fixture or privileged apply gate based on a schema-only digest.
- Neon root-branch recovery, Render live configuration and production backup restore require fresh operator evidence at the time of release; a green PR check cannot certify these.

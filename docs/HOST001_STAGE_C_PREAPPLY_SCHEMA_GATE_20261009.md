# HOST-001 — mandatory offline schema gate before manual Stage C apply

**Status:** CODE CANDIDATE / NO PAID APPLY / NOT ACCEPTED. Date: 2026-10-09.

## Why this gate is needed

The merged PR #99 validates that future AI004-M04B tables appear in backup inventory and in the synthetic Stage C schema digest. This static validation alone does not prove that matching report/cache **rows**, owner references, signed results, or cascade behavior survive a PG18 backup/restore. Previously the manual privileged workflow did not independently run any schema preflight.

The existing bounded Stage C apply had failed on 9 October. Safe Terraform diagnostics and automatic teardown were subsequently improved, but the original provider error was not preserved (**ROOT_CAUSE_NOT_PROVEN**). Successful CI is not live Stage C acceptance.

## Added release boundary

The manual-only `.github/workflows/host001-stage-c-apply.yml` runs a read-only step **before Yandex credentials, Terraform backend initialization, plan and apply**:

```bash
python scripts/host001_stage_c_apply_gate.py --expected-sha "$GITHUB_SHA"
```

That script:

1. Uses the existing offline Alembic chain/fixture check and confirms that the checked-out `git HEAD` is exactly the GitHub run SHA.
2. Requires the currently reviewed synthetic Stage C schema revision `20261002_0023`.
3. Rejects `20261009_0024` or any later revision, even with both matching tables in the backup schema digest. `SCHEMA_INVENTORY_ONLY` is not a completed populated-row restore acceptance.
4. Verifies that the manual workflow contains this exact unbypassed shell step before credentials and that its ordering/identity have not been modified.
5. Produces **only sanitized JSON status**, with `cloud_calls=0`, `database_changes=0` and `authorizes_paid_apply=false`.

The no-cloud HOST-001 CI runs synthetic regression tests for accepted `0023`, rejected schema successors and omitted/repositioned/bypassed manual gate. All changes are source-only. This PR modifies no migrations, database models, Render/Neon configuration, Terraform resource definitions, secrets or deploy settings.

## How to unfreeze Stage C for M04B in the future

**Do not simply switch `APPROVED_STAGE_C_REVISION` to `20261009_0024`.** A separate reviewed successor must first add synthetic matching-report/cache records, check their owner/signature/reference integrity during PG18 post-restore verification, validate inventory and privacy controls, document evidence, pass isolated PostgreSQL and overall CI, then obtain specific owner approval. The new version can then be unlocked through another reviewed change.

## Financial and operator boundary

**This gate cannot authorize another Stage C run.** Earlier approval for a 1,000 RUB / ≤4-hour synthetic test was used and does not carry forward. Before any new billable resource creation: fresh owner approval and cost ceiling, final billing reconciliation, state/orphan check, recovery readiness and review of exact baseline SHA. Real data, Neon migrations, Alice calls and production deployment remain forbidden.

Related: [Issue #78](https://github.com/eletov215/ai-career-agent-site/issues/78), [Issue #80](https://github.com/eletov215/ai-career-agent-site/issues/80), [Draft PR #98](https://github.com/eletov215/ai-career-agent-site/pull/98), [merged PR #99](https://github.com/eletov215/ai-career-agent-site/pull/99), independent plan-only hardening [PR #100](https://github.com/eletov215/ai-career-agent-site/pull/100).

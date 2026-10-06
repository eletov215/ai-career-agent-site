# HOST-001 Stage C execution status — 2026-10-06

| Field | Status |
|---|---|
| Parent | Issue #73 |
| Execution issue | Issue #78 |
| Source main | `b86b523195be6751d973f91be5740eb72310c8bb` |
| Schema | `20261002_0023` |
| Owner direction | START NEXT STAGE |
| Stage C ceiling | 500 RUB total |
| Target live window | <=4 hours |
| Current Render after canonical sync | `dep-db2f5cjncjis73cjgorg` LIVE |
| Production migration | NOT_AUTHORIZED |
| Production data | FORBIDDEN |
| Real-data Alice/provider calls | 0 authorized |
| Email/employer sends | 0 authorized |
| Yandex resources created | 0 |
| Credentialed Terraform plan | NOT_RUN |
| Terraform apply | NOT_RUN |
| Field tests | NOT_RUN |
| Teardown evidence | NOT_RUN |

## Current action

This successor adds a **manual, plan-only** GitHub workflow:
`.github/workflows/host001-stage-c-plan.yml`.

It cannot apply or destroy resources. It exists only to move Stage C from offline validation to an account-aware Terraform plan without asking for Yandex credentials in chat.

The workflow executes only from `main`, requires the exact acknowledgement `PLAN_ONLY_STAGE_C`, uses GitHub Environment `stage-c-yandex`, refuses missing protected inputs, refuses `0.0.0.0/0`, and deletes local key/plan material at the end.

## Protected GitHub Environment inputs

Configure these in GitHub Environment `stage-c-yandex`; never paste their values into an issue, PR, repository file or chat:

- `YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON`
- `YC_STAGE_C_CLOUD_ID`
- `YC_STAGE_C_FOLDER_ID`
- `YC_STAGE_C_ADMIN_CIDR`
- `YC_STAGE_C_SSH_PUBLIC_KEY`
- `YC_STAGE_C_POSTGRES_PASSWORD`
- `YC_STAGE_C_RESTORE_PASSWORD`

The service-account key is materialized only under `$RUNNER_TEMP` and removed in the cleanup step. The workflow uploads no plan/state artifact.

## Plan acceptance gate

The plan is acceptable only if:

1. Yandex authentication succeeds.
2. Account supports the reviewed PostgreSQL 18 / `s3-c2-m8` / zone profile.
3. No destructive/replacement action is present.
4. Every resource address is within the Stage C allowlist.
5. No production resource or production data source is referenced.
6. The account-specific short-test estimate can remain <=500 RUB.
7. The projected recurring launch design remains <=15,000 RUB/month excluding AI/provider usage.

A successful plan does **not** authorize apply by itself.

## Apply blocker

There is intentionally no GitHub apply workflow yet.

Before billable creation, the project still needs:
- reviewed credentialed plan evidence;
- exact account cost/quota evidence;
- an execution/state strategy that guarantees teardown if the runner/session fails;
- owner-visible confirmation that the plan remains inside the already approved Stage C ceiling.

Until those gates are satisfied, Yandex billable resource count remains zero.

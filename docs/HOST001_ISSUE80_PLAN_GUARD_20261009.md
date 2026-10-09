# HOST-001 / Issue #80 — Stage C plan-only defense-in-depth (2026-10-09)

**Status:** CODE CANDIDATE / NO CLOUD CALLS / NO PAID APPLY / NOT A MIG-001 RELEASE.

This successor check adds security assertions to the previously accepted credentialed **plan-only** workflow without changing its cloud scope or its secrets. Historic SHA/evidence and canonical documents remain preserved.

## What the new independent helper enforces

`scripts/host001_stage_c_plan_hardening.py` is dependency-free and is invoked by `scripts/check_host001_package.py` during ordinary HOST-001 static validation.

1. **No hidden Terraform mutation:** the only approved Terraform subcommands in plan-only are one each of `init`, `validate`, `plan` and `show`. Other commands are rejected, including `apply`/`destroy` chained by semicolon/`&&` or Bash line continuation.
2. **No raw plan output:** the single `terraform plan` invocation must match the reviewed redirect to `$RUNNER_TEMP/stage-c-plan.stdout` with both stdout and stderr captured privately. Direct emission, `tee`, `cat` of the plan log, and `set -x` are not approved.
3. **Every active action is reviewed:** only the two currently approved immutable-SHA GitHub actions (`actions/checkout` and `hashicorp/setup-terraform`) are accepted. Mutable refs, `docker://` actions, unreviewed local actions or extra pinned actions require their own review.
4. **Exact secret binding:** every credential expression is allowed only in its already reviewed named shell step **and** in the required environment key (e.g. cloud ID → `TF_VAR_cloud_id`, state secret → `AWS_SECRET_ACCESS_KEY`). A renamed/swapped key, extra secret or dynamic indexed secret expression fails closed.

The HOST-001 no-cloud workflow now triggers for changes to the validator **and** all Stage C workflow YAML files. Regression tests mutate a local in-memory copy of the known-good plan workflow to verify the four security failure categories, without executing Bash, Terraform or third-party actions.

## Scope and limitations

- This is a **reviewed-static-shape** guard, not an unrestricted YAML/Bash parser or a security proof for arbitrary future workflows. Unsupported syntax and added actions/commands deliberately require a new review.
- The guard does not run or authenticate to Yandex Cloud, Neon, Render, Alice, or production. It cannot infer actual costs or infrastructure state.
- **This change does not alter the manual `host001-stage-c-apply.yml` workflow.** The M04B backup/restore schema coverage check (PR #99) runs in static CI; it is not yet independently enforced as a step inside the paid apply workflow. That is a separate pre-apply blocker and must not be represented as resolved.
- Historic Stage C apply failure remains `ROOT_CAUSE_NOT_PROVEN`. Terraform state was confirmed to have no managed resources after manual teardown; cloud billing evidence from 9 October was preliminary. No new paid run is authorized.
- M04B PR #98 remains separately gated: no schema migration, Render/Neon change, merge, provider call or LEGAL release is authorized by this patch.

**Acceptance gate:** full CI, Terraform/static, all mutation regressions green on exact PR head; independent review; explicit user approval before merge. For future MIG-001/real data, separately resolve the remaining privileged workflow/pre-apply checks and a full deployment security review.

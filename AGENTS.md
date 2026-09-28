# Codex repository guide

## Scope

These instructions apply to the whole repository. Keep changes limited to the
requested issue; do not opportunistically reformat or modernize unrelated code.

## Start every delivery

1. Read the complete issue and inspect the current repository state.
2. Verify the remote `main` SHA when GitHub is reachable and record the baseline.
   If it is not reachable, use the checked-out merge-base only with an explicit
   `BLOCKED_GITHUB_ACCESS` note; never imply that remote state was verified.
3. Start a dedicated feature branch. Never commit directly to `main`.
4. Identify applicable package guards before editing protected files.

## Non-negotiable project boundaries

- Do not enable real-data AI: `domain/ai.py::REAL_DATA_SUPPORTED` stays `False`.
- The production legal policy stays `DRAFT / NOT_ACTIVE` until a separately
  authorized legal-activation change.
- Do not make billable Alice/Yandex calls during development or verification.
- Do not change production Render, Neon, or Yandex resources without explicit
  issue scope and authorization.
- Do not weaken, replace, bypass, or regenerate historical package/hash guards
  merely to make a change pass.
- Do not start AI-006 implicitly.

## Repository-local skills

Use the narrowest applicable workflow under `.agents/skills/`:

- `issue-delivery` for implementing a GitHub issue through branch, commit, PR,
  and Actions handoff.
- `package-guard-verification` when planning or running local checks, especially
  around inherited package/hash guards.
- `safety-boundaries` whenever a task could touch AI execution, user data,
  legal state, database schema, deployment, or provider infrastructure.

The skills contain the detailed procedures; do not duplicate them here.

## Completion

Run focused checks plus the inherited offline package/canonical preflight. Report
commands exactly, distinguish failures from unavailable external services, commit
the final diff, and open a PR targeting `main`. Do not merge the PR yourself.

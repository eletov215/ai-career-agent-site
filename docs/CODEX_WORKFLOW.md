# Codex operating workflow

This repository uses a branch-to-PR workflow with explicit responsibility boundaries. GitHub is the source of truth for remote branches, issues, pull requests, and Actions results.

## Responsibilities

### Codex

- Inspect the repository and affected safeguards.
- Implement the smallest accepted change.
- Run local checks and report checks that were not run.
- Prepare a pull request to `main` and review source changes.
- Stop before merge unless the owner explicitly authorizes it.

### GitHub Actions

- Independently verify the proposed change through repository workflows and required checks.

### ChatGPT with GitHub connector or the human owner

- Verify real GitHub state.
- Inspect Actions logs and rerun failed Actions when Codex Cloud cannot.
- Make the final merge decision.

### Owner

- Control production secrets.
- Authorize and perform Render, Neon, and Yandex production changes.
- Approve any billable provider call.

## Status language

Keep `IMPLEMENTED`, `CI_PASS`, `DEPLOYED`, `SITE_QA_PASS`, `LIVE_PROVIDER_PASS`, `QUALITY_PASS`, `LEGAL_PASS`, and `COMPLETE` distinct. A local implementation or passing CI does not imply deployment, production QA, legal approval, or completion. Mark unavailable checks as `NOT_RUN` rather than implying success.

## Example prompts

> Реализуй Issue #N по aca-package-development. Не merge.

> Разбери CI #N по aca-ci-repair. Не меняй код до определения root cause.

> Проверь PR #N по aca-pr-review. Остановись перед merge.

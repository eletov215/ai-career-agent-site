---
name: prepare-main-pr
description: Review, commit, and open a pull request from a repository feature branch into main without merging. Use when a completed change must be delivered as a GitHub pull request with an auditable verification report.
---

# Prepare a pull request to main

1. Confirm the branch is not `main`, the diff matches the issue, and `git status` has no
   unexplained files.
2. Re-run the relevant checks and capture failures or intentionally unrun checks exactly.
3. Commit with a concise imperative subject. Push the current branch and open a PR whose
   base is explicitly `main`; never merge it.
4. In the PR body summarize scope, safety boundaries, tests, and `NOT_RUN` items. Do not
   claim GitHub Actions results until they are observable.
5. Query the PR checks when GitHub is available. Otherwise record
   `BLOCKED_GITHUB_ACCESS` for PR creation and Actions separately.
6. Report baseline SHA, branch, committed head SHA, PR URL/status, changed files, skill
   triggers, tests, Actions, `NOT_RUN`, and unchanged product/runtime/DB/production scope.

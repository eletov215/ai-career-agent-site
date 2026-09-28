---
name: issue-delivery
description: Deliver a repository GitHub issue from verified main through a focused feature branch, local checks, commit, pull request to main, and Actions status reporting. Use when asked to implement, fix, or complete an issue or prepare a PR.
---

# Issue delivery

1. Read the entire issue, including comments and acceptance criteria. Treat the
   issue as the scope authority; do not infer adjacent roadmap work.
2. Inspect `git status`, remotes, branches, recent history, repository guidance,
   relevant docs, workflows, tests, and package guards.
3. Fetch or query remote `main` and record its full SHA before editing. Begin a
   dedicated feature branch at that baseline. If GitHub is inaccessible, do not
   fabricate freshness: record `BLOCKED_GITHUB_ACCESS` and the local HEAD used.
4. Make the smallest coherent change. Review `git diff` for scope drift and
   generated files before testing.
5. Apply `package-guard-verification`; apply `safety-boundaries` when its trigger
   matches. Never substitute a paid or production probe for an offline check.
6. Commit on the feature branch with a focused message. Prepare a PR whose base
   is `main`; include scope, verification, and explicit unavailable checks. Do not
   merge it.
7. Inspect GitHub Actions when access exists. An access failure is
   `BLOCKED_GITHUB_ACCESS`, not a code failure and not a reason to weaken CI.

Final reporting must include baseline SHA, branch, head SHA, PR reference,
changed files, tests, Actions state, `NOT_RUN` items, and preserved boundaries.

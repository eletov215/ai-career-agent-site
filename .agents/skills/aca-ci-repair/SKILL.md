---
name: aca-ci-repair
description: Diagnose and narrowly repair CI, Package preflight, browser QA, Docker, migration, or GitHub Actions failures. Use when a check fails and its real root cause must be established before code changes.
---

# Repair CI

1. Identify the exact workflow, run, job, and step.
2. Read the actual failing log.
3. Classify the failure as `code defect`, `test defect`, `dependency issue`, `external transient`, `infrastructure`, or `unknown`.
4. For a likely transient and safe failure, rerun failed jobs before changing code.
5. If the failure reproduces, compare it with the last known good commit.
6. Make the narrowest possible fix.
7. Never use `continue-on-error`, delete checks, weaken package guards, weaken hash/evidence validation, make arbitrary dependency changes, or hide real failures.
8. Rerun CI.
9. Report the exact root cause.
10. Explicitly state whether source code changed.

If GitHub Actions or its API is inaccessible, report `BLOCKED_GITHUB_ACCESS` and do not claim resolution.

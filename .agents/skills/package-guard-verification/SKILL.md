---
name: package-guard-verification
description: Select and run offline checks without weakening inherited package, canonical-document, or hash protections. Use when changing guarded files, CI, package evidence, or when validating a change before commit or PR.
---

# Package guard verification

## Discover

- Read the relevant checker in `scripts/check_*_package.py`, its test in
  `tests/test_*_package.py`, and the workflow invoking it before changing guarded
  paths.
- Treat recorded baselines, successor maps, manifests, and historical evidence
  as review controls, not snapshots to refresh automatically.

## Verify

1. Run the narrow tests for changed behavior or documents.
2. Run `python -S -m unittest tests.test_legal001_canonical -v`; it is the
   dependency-free inherited package/canonical preflight used by CI.
3. Run `pytest -q` when dependencies and time permit. If not, report the exact
   limitation and retain the focused and offline results.
4. Inspect `git diff --check`, `git status --short`, and the final path list.

Never edit expected hashes or remove a negative assertion solely to obtain a
pass. If an intentional in-scope change conflicts with a historical guard, add a
reviewable successor boundary following the existing pattern and preserve the
older assertion. Do not invoke provider-live, deployment, PostgreSQL-live, or
billable jobs as a default verification step.

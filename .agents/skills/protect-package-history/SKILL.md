---
name: protect-package-history
description: Preserve this repository's accepted package lineage, canonical evidence, pinned hashes, and safety gates. Use when changing package documentation, package checks, workflows, canonical status, AI or legal boundaries, or any file covered by historical guards.
---

# Protect package history

- Identify affected `scripts/check_*_package.py`, `tests/test_*_package.py`, canonical
  documents, workflow gates, and fixed predecessor hashes before editing.
- Treat accepted evidence and historical snapshots as immutable. Add a new status or
  evidence layer rather than editing old facts.
- Never delete assertions, broaden allowlists, replace exact hashes with loose matching,
  or skip a predecessor gate to obtain green output.
- Keep real-data AI closed: assert `REAL_DATA_SUPPORTED is False`, legal policy is
  `DRAFT`, and live/billable provider calls are zero whenever the task touches AI policy.
- Run each affected package check directly and its test wrapper. Record commands and
  distinguish local results from GitHub Actions results.
- If a required historical artifact is unavailable or inconsistent, stop and report the
  exact blocker; do not regenerate or guess it.

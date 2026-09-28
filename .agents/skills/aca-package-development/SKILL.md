---
name: aca-package-development
description: Implement an approved package, GitHub issue, or focused product change through a minimal, guarded branch-and-PR workflow. Use when delivering an accepted repository change without merging it.
---

# Develop a package

1. Verify the remote `main` baseline. If GitHub is unavailable, say so; never present local knowledge as remote state.
2. Read the issue and acceptance criteria.
3. Inspect affected code, documentation, tests, workflows, and package guards.
4. Identify the minimal change boundary.
5. Create a feature branch from the verified `main`.
6. Implement only the minimal change.
7. Run relevant tests plus inherited and package guards.
8. Verify diff scope and repository hygiene.
9. Commit the change.
10. Open a PR specifically against `main`.
11. Inspect GitHub Actions when available.
12. Fix only the root cause; never weaken tests or guards.
13. Stop before merge unless the owner explicitly authorizes it.
14. Produce an evidence report that explicitly lists `NOT_RUN` items.

## Historical package protections

- Discover existing package, hash, and evidence checks before editing.
- Preserve historical artifacts and their validation semantics.
- Run every inherited guard relevant to the touched area and report its exact result.
- If an intended change conflicts with a historical guard, stop and escalate the conflict instead of altering, bypassing, regenerating, or deleting the guard.

---
name: deliver-github-issue
description: Deliver a repository GitHub issue from an up-to-date main baseline through a scoped implementation, local verification, commit, and unmerged pull request. Use when asked to implement, fix, or complete a numbered issue in this repository.
---

# Deliver a GitHub issue

1. Read the complete issue and acceptance criteria before proposing changes.
2. Check GitHub authentication and fetch `main`. Record `git rev-parse origin/main`,
   create a feature branch at that commit, and confirm the worktree is understood.
3. If GitHub cannot be read, state `BLOCKED_GITHUB_ACCESS`; use only a clearly identified
   local baseline and do not claim the issue or remote branch was verified.
4. Inspect nearby implementation, `.github`, `docs`, tests, and inherited package guards.
5. Make only changes required by the issue. Apply the boundaries in the root
   `AGENTS.md`; for package/history work also use `protect-package-history`.
6. Review `git diff`, run targeted tests followed by affected inherited gates, and
   verify no secrets or generated noise entered the patch.
7. Commit once the patch is coherent. Then use `prepare-main-pr` to publish an unmerged
   PR to `main` and produce the delivery report.

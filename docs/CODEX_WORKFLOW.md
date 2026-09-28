# CODEX-OPS-001 — repository-local Codex workflow

## Purpose

This developer-workflow package gives Codex a small, repository-owned operating layer.
It does not change the site, application runtime, database schema, deployment providers,
or production state.

## Discovery model

Codex reads the root `AGENTS.md` for repository-wide constraints. Reusable procedures
live in `.agents/skills/<skill-name>/SKILL.md`, the supported repository-scoped skill
layout. A skill's YAML `name` and `description` are its trigger metadata; its body is
loaded only when the task matches. This keeps `AGENTS.md` short and avoids duplicating
procedures.

## Included skills

| Skill | Trigger |
|---|---|
| `deliver-github-issue` | Implementing, fixing, or completing a numbered repository issue |
| `protect-package-history` | Touching package/canonical docs, package guards, workflows, evidence, or AI/legal boundaries |
| `prepare-main-pr` | Committing completed work and opening an unmerged PR to `main` |

## Standard issue-to-PR flow

1. Read the issue and repository instructions.
2. Authenticate to GitHub, fetch `main`, and record `origin/main` as the baseline SHA.
3. Create one feature branch from that exact baseline.
4. Inspect the relevant implementation and inherited guards, then make a scope-limited
   patch.
5. Run targeted and inherited checks without real data or paid provider calls.
6. Review and commit the patch, push the branch, and open a PR with base `main`.
7. Observe, but never invent, GitHub Actions state. Do not merge the PR.

If GitHub is inaccessible, use the literal status `BLOCKED_GITHUB_ACCESS`. A local commit
may still be prepared when useful, but it is not a substitute for verifying current
`main`, opening the PR, or observing Actions.

## Stable safety boundary

- `REAL_DATA_SUPPORTED=False` remains unchanged.
- Legal policy remains `DRAFT`; policy activation is a separate approved change.
- Billable Alice/Yandex calls remain zero.
- Existing package/hash guards and historical evidence are not weakened.
- AI-006 is not started.
- Runtime, migrations, Render, Neon, and Yandex production are out of scope unless a
  future issue explicitly brings one of them into scope.

## Local validation

For workflow-only changes, validate Markdown/YAML structure, skill frontmatter, clean
diff scope, and the existing offline canonical/package preflight. Use the skill creator's
`quick_validate.py` for every changed skill when available. Application test suites are
only necessary when application files change or an inherited guard requires them.

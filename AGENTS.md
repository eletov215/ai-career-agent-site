# Repository operating rules

These rules apply to the whole repository.

## Start every task

1. Read the requested GitHub issue in full; treat it as the scope contract.
2. Fetch `main`, record its exact SHA, and create a dedicated feature branch from that
   commit. If GitHub is unreachable, report `BLOCKED_GITHUB_ACCESS` and never invent
   remote state.
3. Inspect the files, tests, workflows, and package guards relevant to the request
   before editing. Follow more specific `AGENTS.md` files if any are added later.
4. Keep unrelated working-tree changes intact and keep the patch inside the issue scope.

## Non-negotiable project boundaries

- Never use real applicant data, secrets, provider credentials, or production data in
  development or evidence.
- External provider calls are mocked by default. Billable Alice/Yandex calls must remain
  zero unless an issue explicitly authorizes a controlled live verification.
- Do not change production runtime, database schema, Render, Neon, or Yandex resources
  unless the issue explicitly requires that exact change.
- Preserve `domain/ai.py` with `REAL_DATA_SUPPORTED = False` and preserve the legal AI
  policy as `DRAFT` unless a separately approved activation issue explicitly says otherwise.
- Do not begin AI-006 implicitly.
- Historical package tests, pinned hashes, evidence, and predecessor gates are
  append-only constraints. Never weaken or rewrite them merely to make a check pass.

## Delivery

- Use the relevant repository skill under `.agents/skills/`; the skills contain the
  detailed procedures and should not be copied into this file.
- Run the narrow checks for the change and all affected inherited/package guards.
- Commit the reviewed diff, push the feature branch, and open a pull request targeting
  `main`. Never merge it yourself.
- Report baseline SHA, branch, head SHA, PR URL, changed files, checks, remote Actions
  state, and anything not run. Mark inaccessible GitHub state as
  `BLOCKED_GITHUB_ACCESS`.

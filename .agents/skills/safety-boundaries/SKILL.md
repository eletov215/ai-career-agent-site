---
name: safety-boundaries
description: Protect this repository's production, data, legal, and paid-provider boundaries. Use when work touches AI/provider paths, personal or real data, consent/legal policy, migrations, Render/Neon/Yandex infrastructure, deployment, or live verification.
---

# Safety boundaries

Before editing, classify the proposed paths as application runtime, database,
deployment/infrastructure, provider execution, legal/consent, or offline tooling.
Stop and report an out-of-scope dependency rather than expanding the issue.

For every applicable change, confirm all of the following after the diff:

- `domain/ai.py` still declares `REAL_DATA_SUPPORTED = False`.
- `services/legal_policy.py` still declares the reviewed production policy as
  `DRAFT` and inactive.
- no migration or database schema file changed unless explicitly required;
- no `render.yaml`, Neon, or Yandex production configuration changed unless
  explicitly required;
- no command made a live or billable Alice/Yandex request;
- no AI-006 implementation was introduced;
- inherited safety assertions and historical package/hash guards still run.

Prefer static checks, fakes, fixtures, synthetic data, and offline tests. Never
turn on a production flag, insert a real credential, relax consent/admission, or
run a live probe merely to demonstrate readiness. List prohibited live checks as
`NOT_RUN` with the reason.

# AI Career Agent — project guide

```text
canonical plan: docs/PLAN_CURRENT.md v1.4.20
passport: docs/PROJECT_PASSPORT.md v2.34
current package: PROF-001 / НУЖНА ПРОВЕРКА
production revision: 20260811_0009
candidate revision: 20260811_0010
WSGI: app:app
```

## Required workflow

1. Use current GitHub ZIP/main only.
2. Change one package in a separate branch.
3. Open Pull Request; wait for all CI including dedicated package gate.
4. Merge only when green.
5. Verify Render revision/readiness.
6. Run package E2E/regression.
7. Mark complete only with measured evidence.
8. Return full ZIP, patch ZIP and canonical docs.

## PROF-001 E2E

Follow `docs/PROF001_RUNBOOK.md`: partial save, relogin, material version, unchanged no-op, historical read, owner isolation, stale conflict, restart persistence and AUTH/OAuth/search regression.

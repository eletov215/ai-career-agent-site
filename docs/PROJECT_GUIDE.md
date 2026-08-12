# AI Career Agent — project guide

```text
canonical plan: docs/PLAN_CURRENT.md v1.4.23
passport: docs/PROJECT_PASSPORT.md v2.37
current package: PROF-002 / НУЖНА ПРОВЕРКА
production revision: 20260811_0010
candidate revision: 20260812_0011
verified base commit: f5e513f0f992b20305fbef36851ef97576013c86
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

## PROF-002 E2E

Follow `docs/PROF002_RUNBOOK.md`:

- upload authenticated text PDF;
- verify editable review and no persistence before confirm;
- edit/delete suggestions and confirm;
- verify source/provenance history without raw content;
- test existing confirmed scalar conflict;
- reject non-PDF, corrupt/image-only/over-limit input;
- reject foreign/expired/tampered token, missing CSRF and stale base version;
- verify relogin/restart/mobile behavior;
- check AUTH/OAuth/search regression and secret-free logs.

## Security reminders

Never commit or share resume content, review token, cookies, OAuth secrets, `.env`, `DATABASE_URL`, backups or dumps. External API/network calls remain mocked in CI unless a package explicitly requires real E2E after deploy.

# AI Career Agent — project guide

```text
canonical plan: docs/PLAN_CURRENT.md v1.4.29
passport: docs/PROJECT_PASSPORT.md v2.43
PROF-003: ВЫПОЛНЕНО
PRIV-001: ВЫПОЛНЕНО
current package: SEARCH-005 / ГОТОВО К СТАРТУ
production revision: 20260813_0013
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

## PROF-003 development rule

Do not reintroduce authoritative localStorage writes. Draft document data is server-owned and owner-scoped. PROF-001 profile facts may seed a draft but draft edits must not become confirmed facts without a separate confirmation contract.


## PRIV-001 E2E

Use a throwaway verified account because account deletion is destructive. Verify owner-readable ZIP export (`manifest.json`, `data.json`, owned resume image assets) with no password/session/token/OAuth credentials; wrong confirmation phrase/password must not delete anything; exact phrase + current password must delete the account and local HH/SuperJob credentials; old login must fail; retention cleanup must leave active accounts intact; audit/logs must contain aggregate counts only. After deploy `/health/ready` must show revision `20260813_0013`.

Do not claim remote provider-side OAuth grant revocation: current PRIV-001 scope guarantees local credential erasure only.

## SEARCH-005 start boundary

Before implementation audit existing `services/source_status.py`, observability/provider metrics, SyncRun/checkpoint state, diagnostics/admin authorization options and templates. Detailed admin telemetry must be inaccessible without explicit admin authorization and must not expose credentials, token material, resume/profile PII or raw provider bodies. Production baseline revision is `20260813_0013`.

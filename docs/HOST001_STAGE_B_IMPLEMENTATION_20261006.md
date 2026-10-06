# HOST-001 / Issue #73 Stage B — implementation successor

Date: 2026-10-06  
Status: IMPLEMENTED_CANDIDATE / NO APPLY / NO PRODUCTION MIGRATION  
Baseline main: `40492010857559e73dd47d37af3d6bb1e04b7322`  
Application schema: `20261002_0023` unchanged

## Owner-approved scope

Offline code/PR preparation for the Russia launch topology: one application server and one private Managed PostgreSQL host within the approved budget. The future two-host database path remains represented but is not activated or purchased.

## Implemented candidate controls

- Managed PostgreSQL target updated to PostgreSQL 18.
- Explicit `single` default host profile plus retained `two` profile with different-zone precondition.
- Yandex-only non-root PostgreSQL 18 ops image; shared Render Dockerfile remains unchanged.
- Compose migration and background writers are opt-in profiles so default rehearsal cannot automatically migrate, sync vacancies or run privacy cleanup.
- Yandex ops supplies strict libpq `PGSSLMODE=verify-full`, mounted CA and `PGTARGETSESSIONATTRS=read-write` without changing inherited shared backup code.
- Encrypted backup + manifest can be exported off-VM only through explicit HTTPS presigned S3-compatible URLs after manifest/size/SHA-256 checks.
- Yandex Caddy strips client-supplied `CF-Connecting-IP` and rebuilds `X-Forwarded-For` from the observed peer.
- Updated package guard/tests and operational successor records.

## Safety boundary

No Terraform apply, cloud credentials, production database access, schema migration, Render/Neon/Yandex production change, provider call, email/employer send or legal activation is authorized by this Stage B implementation.

`REAL_DATA_SUPPORTED=False` and legal policy `DRAFT` remain required.

## Verification state at handoff

The earlier Codex task reported local tests passing but its commit was not published to GitHub. This successor branch recreates the reviewed Stage B intent so independent GitHub CI can establish exact-head evidence.

Until GitHub Actions run against the published branch/PR:
- CI_PASS: NOT_RUN
- DEPLOYED: NOT_RUN
- SITE_QA_PASS: NOT_RUN
- PG18 TLS/restore field drill: NOT_RUN
- LEGAL_PASS: NOT_CLAIMED
- COMPLETE: NOT_CLAIMED

Field/cloud stages C–E remain separately owner-gated.

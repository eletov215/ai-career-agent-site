# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.29 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.43 |
| Завершённый пакет | `PRIV-001 — ВЫПОЛНЕНО` |
| Текущий пакет | `SEARCH-005 — ГОТОВО К СТАРТУ` |
| Production revision | `20260813_0013` |

> GitHub является главным источником кода. PRIV-001 завершён и подтверждён в production; следующий кодовый пакет SEARCH-005. Actual `.env`, secrets/tokens, DB/dumps/backups, virtualenv, caches и bytecode не входят в repository/release ZIP; `infra/vps/.env.example` остаётся обязательным secret-free template.

## 1. Назначение

AI Career Agent — Flask/Gunicorn web-service карьерного сопровождения. WSGI entrypoint `app:app`. PROF-001/002/003 и PRIV-001 завершены; следующий SEARCH-005 добавит защищённый admin center состояния источников перед AI-контуром.

## 2. PRIV-001 complete

```text
first-party User
-> /privacy-center
-> readable ZIP export
-> exact phrase + current password deletion
-> local Auth/OAuth/Profile/Resume cleanup
-> identifier-free privacy audit
-> periodic technical retention cleanup
```

Export содержит owner data и owned resume image assets, но не password/session/token hashes и не OAuth access/refresh credentials. Account deletion удаляет local HH/SuperJob credential mirrors; remote provider-side grant revoke не заявляется.

## 3. Retention baseline

```text
pending unverified account       30 days
expired/revoked auth artifacts   30 days
orphan ResumeAsset                7 days
identifier-free privacy audit   180 days
cleanup interval                  24 hours
active owner content              until explicit deletion
```

Это технические defaults. Финальные legal wording/retention фиксируются `LEGAL-001`.

## 4. Persistence

Migration `20260813_0013` применена в production; `privacy_audit_events` не содержит User FK/email/content. Existing AUTH/PROF/RESUME schema не меняется.

## 5. Verification

```text
local compile/migration/focused tests      passed
GitHub full workflow + dedicated PRIV gate green
Render current=expected 0013               passed
privacy cleanup worker healthy             passed
export/secret/assets E2E                    passed
throwaway delete/owner isolation E2E       passed
restart/regression/log review               passed
```

## 6. Workflow

```text
PRIV-001 COMPLETE
-> SEARCH-005 audit current source-state/OPS/SYNC/admin boundaries
-> implement in feature branch
-> Pull Request / CI / Render / E2E
```

## 7. Documentation

- `docs/PRIV001_IMPLEMENTATION.md`
- `docs/PRIV001_VERIFICATION_STATUS.md`
- `docs/PRIV001_RUNBOOK.md`
- `docs/PRIV001_PRIVACY_REFERENCE.md`
- `docs/PRIV001_SECURITY_REFERENCE.md`
- `docs/PROF003_*` — COMPLETE evidence
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/SOURCE_AUDIT.md`

## 8. Rollback

Application revert может оставить additive `0013`. Downgrade `0013 -> 0012` удаляет только identifier-free privacy audit table. Уже выполненное account deletion не восстанавливается schema rollback.

## 9. Hosting

Render остаётся staging/резервной площадкой. Реальный VPS test `INFRA-001`, production host/domain migration и owned-domain transactional sender выполняются в предрелизном инфраструктурном окне.

## Current package
SEARCH-005 admin source status center is implemented as a candidate on revision `20260819_0014`. It requires `SEARCH_ADMIN_EMAILS` and remains NEEDS VERIFICATION until CI/Render/E2E.

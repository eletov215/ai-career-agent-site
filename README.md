# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.27 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.41 |
| Завершённый пакет | `PROF-003 — ВЫПОЛНЕНО` |
| Текущий пакет | `PRIV-001 — НУЖНА ПРОВЕРКА` |
| Production revision | `20260812_0012` |
| Candidate revision | `20260813_0013` |

> GitHub является главным источником кода. PRIV-001 candidate построен поверх подтверждённого PROF-003 baseline. Actual `.env`, secrets/tokens, DB/dumps/backups, virtualenv, caches и bytecode не входят в repository/release ZIP; `infra/vps/.env.example` остаётся обязательным secret-free template.

## 1. Назначение

AI Career Agent — Flask/Gunicorn web-service карьерного сопровождения. WSGI entrypoint `app:app`. PROF-001/002/003 завершены; текущий PRIV-001 добавляет фактический пользовательский контроль над данными перед AI-контуром.

## 2. PRIV-001 candidate

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
identifier-free privacy audit   180 days
cleanup interval                  24 hours
active owner content              until explicit deletion
```

Это технические defaults. Финальные legal wording/retention фиксируются `LEGAL-001`.

## 4. Persistence

Migration `20260813_0013` добавляет только `privacy_audit_events` без User FK/email/content. Existing AUTH/PROF/RESUME schema не меняется. Production остаётся `0012` до merge/deploy.

## 5. Verification

```text
local compile/migration/focused tests      passed
SQLite 0012 -> 0013 -> 0012 -> 0013       passed
Alembic check                              passed
Jinja / hygiene / infra                    passed
full Flask/PostgreSQL route gate           GitHub CI required
Render 0013 + destructive throwaway E2E    required
```

## 6. Workflow

```text
branch priv-001-candidate-v1.4.27
-> Pull Request
-> full green CI
-> merge main
-> Render migration 0013
-> export/delete/restart/log E2E on throwaway account
-> PRIV-001 COMPLETE
-> SEARCH-005
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

# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.25 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.39 |
| Текущий пакет | `PROF-003 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `PRIV-001 — следующий после закрытия PROF-003` |
| Production revision | baseline `20260812_0011`; candidate `20260812_0012` |
| Проверенная основа | GitHub `main` ZIP comment `427b2726edd078993a3c26985e17713cf2e76c9e` |

> GitHub является главным источником кода. Загруженный `ai-career-agent-site-main (16).zip` проверен: functional code соответствует PROF-002 COMPLETE; 11 repository docs синхронизированы с canonical v1.4.24 перед PROF-003. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий или release ZIP.

## 1. Назначение

AI Career Agent — Flask/Gunicorn-сервис карьерного сопровождения. WSGI entrypoint `app:app`. PROF-001/002 завершены; PROF-003 candidate переводит resume builder с localStorage на server-side owner-scoped drafts.

## 2. PROF-003 — НУЖНА ПРОВЕРКА

```text
first-party owner
-> /resumes library
-> current server draft + optimistic revision autosave
-> durable photo/logo assets
-> explicit checkpoint/export/restore
-> immutable version history
```

Draft text остаётся document content, а не canonical PROF-001 facts. Draft можно один раз seed-ить из подтверждённого profile; обратного auto-sync нет.

## 3. Persistence

Migration `20260812_0012` создаёт `resume_drafts`, `resume_versions`, `resume_assets`, `resume_exports`. PDF binary остаётся в браузере; server хранит только export metadata tied to immutable version.

## 4. Проверки

```text
split full available pytest                 252 passed, 11 skipped
focused PROF-003 checks                     15 passed, 1 skipped
compileall / Jinja / JavaScript syntax      passed
SQLite migration round-trip to 0012         passed
Alembic / architecture / hygiene / infra     passed
Flask/PostgreSQL route gate                  GitHub CI required
Render current/expected 0012 + E2E           required
```

## 5. Workflow

```text
PROF-003 CANDIDATE
-> branch + Pull Request
-> green CI
-> Render migration 0012
-> autosave/history/restore/assets/export/restart/mobile E2E
-> PROF-003 COMPLETE
-> PRIV-001
```

## 6. Документация

- `docs/PROF003_IMPLEMENTATION.md`
- `docs/PROF003_VERIFICATION_STATUS.md`
- `docs/PROF003_RUNBOOK.md`
- `docs/PROF003_RESUME_REFERENCE.md`
- `docs/PROF003_SECURITY_REFERENCE.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/SOURCE_AUDIT.md`

## 7. Rollback

Application revert может оставить additive `0012`. Downgrade `0012 -> 0011` удаляет PROF-003 tables и является data-destructive после реального использования.

## 8. Ограничения

Нет AI interview/rewrite, public sharing, collaborative merge, stored PDF binary и external object provider. PostgreSQL asset storage — staging baseline; privacy export/delete/retention остаётся PRIV-001.

## 9. Hosting

Render остаётся staging/резервной площадкой. Реальный VPS test `INFRA-001`, production host/domain migration и domain email sender выполняются в предрелизном окне.

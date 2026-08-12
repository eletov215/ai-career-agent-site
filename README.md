# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.23 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.37 |
| Текущий пакет | `PROF-002 — НУЖНА ПРОВЕРКА` |
| Следующий после завершения | `PROF-003` |
| Production revision | `20260811_0010` |
| Candidate database revision | `20260812_0011` |
| Проверенная основа | GitHub `main` commit `f5e513f0f992b20305fbef36851ef97576013c86` |

> GitHub является главным источником кода. Загруженный `ai-career-agent-site-main (16).zip` проверен и полностью совпадает с текущим `main`. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий или release ZIP.

## 1. Назначение

AI Career Agent — Flask/Gunicorn-сервис карьерного сопровождения. WSGI entrypoint остаётся `app:app`. SEARCH-001..004, AUTH-001/002 и PROF-001 завершены. PROF-002 добавляет import существующего текстового PDF-резюме в подтверждённый PROF-001 через обязательный editable review.

## 2. PROF-002 candidate

```text
first-party authenticated owner
-> upload one bounded text PDF
-> request-local pypdf extraction
-> deterministic proposal + confidence/warnings/conflicts/evidence
-> full editable PROF-001 review
-> explicit confirm POST
-> validation + expected version + row lock
-> immutable confirmed version with aggregate provenance
```

Ключевые инварианты:

- до confirm профиль и история не меняются;
- upload bytes, raw text и unconfirmed proposal не сохраняются;
- existing confirmed scalar values не заменяются молча;
- signed review token действует 30 минут, owner/version-bound и не содержит filename/text/facts;
- user может исправить или удалить любое предложение;
- OCR, DOC/DOCX, LLM/AI parsing, provider import и persisted drafts исключены;
- canonical profile schema остаётся `1`.

Новые/расширенные маршруты:

```text
GET/POST /profile/import
POST     /profile/import/confirm
GET      /profile/history/<version>
```

## 3. Persistence

Alembic `20260812_0011` добавляет к `career_profile_versions`:

```text
source_kind      manual | resume_import
provenance_json  bounded aggregate extraction/review metadata
```

Filename, text, contacts, excerpts и profile payload не входят в provenance. Existing versions получают `manual` и `{}`.

## 4. Локальные проверки

```text
full available pytest:                    246 passed, 10 skipped
focused PROF-002/PROF-001/parser:         15 passed
architecture/template/document subset:    23 passed
compileall:                                passed
Jinja parse:                               22 templates passed
SQLite 0011 -> 0010 -> 0011:               passed
Alembic check:                             passed
```

Flask/Psycopg/PostgreSQL skips подтверждаются Pull Request CI. В workflow добавлен dedicated `Verify PROF-002 resume import review controls`.

## 5. Правильный workflow

```text
branch prof-002-candidate-v1.4.23
-> Pull Request to main
-> all CI green
-> merge
-> Render current_revision=expected_revision=20260812_0011
-> positive/negative/privacy/owner/stale/restart/mobile E2E
-> PROF-002 COMPLETE
```

До полного внешнего gate статус остаётся `НУЖНА ПРОВЕРКА`.

## 6. Документация

- `docs/PROF002_IMPLEMENTATION.md`
- `docs/PROF002_VERIFICATION_STATUS.md`
- `docs/PROF002_RUNBOOK.md`
- `docs/PROF002_EXTRACTION_REFERENCE.md`
- `docs/PROF002_SECURITY_REFERENCE.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/SOURCE_AUDIT.md`

## 7. Rollback

Application revert может оставить additive revision `0011`; предыдущий код игнорирует новые audit columns. Controlled downgrade `0011 -> 0010` удаляет source/provenance metadata, но не current profile и confirmed snapshots. Raw resume content нельзя добавлять в rollback artifacts.

## 8. Ограничения

Deterministic parser не является AI. Image-only PDF fail closed без OCR. Review не является persisted draft и теряется при refresh/expiry. Render остаётся staging/резервной площадкой; собственный VPS/domain и domain email sender остаются pre-release scope.

## 9. Hosting

Render остаётся staging/резервной площадкой. Реальный VPS test `INFRA-001`, production host/domain migration и domain email sender выполняются в предрелизном окне.

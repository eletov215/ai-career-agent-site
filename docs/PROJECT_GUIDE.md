# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Более новый ZIP текущего чата становится рабочей основой.
3. Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4. Главный entrypoint — `app.py`, WSGI — `app:app`; `app_fixed.py` не используется.

## 2. Текущий пакет

```text
AUTH-002 — НУЖНА ПРОВЕРКА
baseline: ai-career-agent-site-main (12).zip
candidate revision: 20260811_0009
production before deploy: 20260810_0008
```

## 3. Обязательный цикл

```text
актуальный ZIP + canonical docs
→ один package ID
→ inventory/risks/rollback
→ code + positive/negative tests
→ full ZIP + patch ZIP
→ green GitHub Actions
→ Render migration/API/E2E
→ final status/docs
```

## 4. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q .
python -m pytest -q
python -m alembic check
```

## 5. AUTH-002 rules

- First-party `User` is the only browser identity.
- Connect routes require an active server-side auth session.
- OAuth state is one-time, TTL-bound and tied to `user_id` + `auth_session_id`.
- Never auto-link by email.
- Never overwrite another User connection.
- Tokens remain encrypted and secret-free in logs/public copy.
- Disconnect is owner-scoped POST + CSRF.
- Existing app-level SuperJob public-search credential is independent of user OAuth.

## 6. External verification

Use `docs/AUTH002_RUNBOOK.md`. Real provider codes/tokens/client secrets must never be pasted into chat, logs, screenshots or GitHub.

## 7. Artifacts

Every code candidate returns:

```text
full project ZIP
patch ZIP with changed/new files only
PLAN_CURRENT MD/DOCX/PDF
PROJECT_PASSPORT MD/DOCX/PDF
SOURCE_AUDIT MD/DOCX/PDF
package-specific MD/DOCX/PDF
canonical ZIP + checksums
```

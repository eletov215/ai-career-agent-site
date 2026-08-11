# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Более новый ZIP текущего чата становится рабочей основой.
3. Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4. Главный entrypoint — `app.py`, WSGI — `app:app`; `app_fixed.py` не используется.

## 2. Текущий пакет

```text
AUTH-001 — НУЖНА ПРОВЕРКА
branch: auth-001-first-party-account
commit: auth: add first-party account and revocable sessions
candidate revision: 20260810_0008
production current revision: 20260810_0008
```

## 3. Обязательный цикл

```text
актуальный ZIP + canonical docs
→ один package ID
→ inventory/risks/rollback
→ code + tests
→ branch/PR
→ green GitHub Actions
→ Render/API/E2E smoke
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

GitHub Actions должен выполнить dedicated AUTH-001, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH regressions, backup/restore и container smoke.

## 5. AUTH-001 production verification

1. Current Render Free staging uses `AUTH_EMAIL_BACKEND=gmail_api`; Gmail OAuth Client ID/Secret/Refresh Token remain only in environment and tests mock Google HTTP calls.
2. `/health/ready` revision `20260810_0008`, `auth.email_backend=gmail_api`, configured true; real success still requires `auth_email_delivered` and message receipt.
3. Register unique user and verify email.
4. Login, create second session, revoke it, logout current.
5. Forgot/reset; old token/password/sessions invalid.
6. CSRF/rate limits/no-store/strict-origin/open-redirect and secret-free logs; production Safari form POST must pass without weakening `WTF_CSRF_SSL_STRICT`.
7. Before beta/commercial release replace personal Gmail API with a project-owned domain sender and SPF/DKIM/DMARC; AUTH business logic remains provider-neutral.

## 6. Неприкосновенные правила

- No `.env`, credentials, databases, dumps, backups, virtualenv, caches or bytecode in release.
- Password/action/session plaintext never stored/logged.
- Existing HH/SJ connections are not auto-bound.
- Production schema changes only through Alembic.
- AUTH-001 does not modify search/sync semantics.

## 7. Rollback

Application revert. Keep additive `0008` after any real account. Downgrade only before account creation or after verified backup and explicit owner decision.

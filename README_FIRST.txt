AI Career Agent — AUTH-001 candidate v1.4.13

1. Создать ветку от актуального main:
   auth-001-first-party-account

2. Скопировать полный архив с заменой файлов. Папку .git не удалять.

3. Проверить наличие:
   routes/auth.py
   services/auth.py
   services/passwords.py
   services/email_delivery.py
   repositories/auth.py
   models/auth.py
   migrations/versions/20260810_0008_first_party_auth.py
   templates/auth/
   tests/test_auth_*.py
   docs/AUTH001_*.md

4. Commit:
   auth: add first-party account and revocable sessions

5. Merge только после полностью зелёного GitHub Actions, включая:
   Verify AUTH-001 first-party account controls

6. До production E2E настроить SMTP secrets по docs/AUTH001_RUNBOOK.md.
   Не публиковать значения в GitHub, ZIP или чат.

7. Render Start Command не менять. После deploy ожидать revision 20260810_0008.

8. Выполнить register/verify/login/two-session revoke/logout/forgot/reset smoke.

AUTH-001 остаётся НУЖНА ПРОВЕРКА до green CI, Render 0008, SMTP и полного E2E.

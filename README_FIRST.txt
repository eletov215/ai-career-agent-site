AI Career Agent — AUTH-001 Gmail API HTTPS staging candidate v1.4.16

1. Upload the full archive to current GitHub main/working branch with replacement.
2. Do not create app_fixed.py; WSGI remains app:app.
3. No database migration is added; expected revision remains 20260810_0008.
4. Merge/deploy only after GitHub Actions is fully green, including AUTH-001/config/infra gates.
5. Render Free staging email transport is Gmail API over HTTPS, not SMTP.
6. Keep OAuth Client ID, Client Secret and Refresh Token only in Render Environment; never commit or paste them into chat.
7. After deploy set AUTH_EMAIL_BACKEND=gmail_api and verify /health/ready, auth_email_delivered and real email receipt.
8. Continue full AUTH-001 register/verify/login/session-revoke/logout/reset E2E.
9. Gmail API is staging-only; before beta/commercial release migrate to a project-owned domain sender with SPF/DKIM/DMARC.

AUTH-001 remains НУЖНА ПРОВЕРКА until real Gmail API delivery and full E2E are complete.

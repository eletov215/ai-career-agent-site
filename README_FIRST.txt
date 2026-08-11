AI Career Agent — AUTH-001 Mail.ru SMTP SSL/TLS fallback v1.4.15

1. Upload this full archive to the current GitHub main/working branch with replacement.
2. Do not create app_fixed.py; WSGI remains app:app.
3. No database migration is added; expected revision remains 20260810_0008.
4. Merge only after GitHub Actions is fully green, including AUTH-001/config/infra gates.
5. In Render switch staging mail sender to Mail.ru using smtp.mail.ru:465 and implicit SSL/TLS.
6. Keep AUTH_SMTP_USE_TLS=0 and set AUTH_SMTP_USE_SSL=1. Never enable both.
7. Use the full Mail.ru email as AUTH_SMTP_USERNAME/AUTH_EMAIL_FROM and the external-app password only in Render Environment.
8. Redeploy, confirm /health/ready status=ok and email backend configured=true.
9. Run resend verification / registration and confirm auth_email_delivered, then continue full AUTH-001 E2E.

AUTH-001 remains НУЖНА ПРОВЕРКА until real Mail.ru delivery and full E2E are complete.

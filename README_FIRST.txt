AI Career Agent — AUTH-001 Safari CSRF hotfix v1.4.14

1. Upload this full archive to the current GitHub main/working branch with replacement.
2. Do not create app_fixed.py; WSGI remains app:app.
3. No database migration or Render environment variable change is required.
4. Merge only after GitHub Actions is fully green, including AUTH-001 gate.
5. Render redeploy. Confirm /health/ready remains revision 20260810_0008 and SMTP configured.
6. Repeat Safari/iPhone registration. The valid form POST must no longer return the CSRF missing-referrer 400.
7. Continue full AUTH-001 E2E: verification, login, two sessions, revoke, logout, forgot/reset, old password/session invalidation.

AUTH-001 remains НУЖНА ПРОВЕРКА until that production E2E is complete.

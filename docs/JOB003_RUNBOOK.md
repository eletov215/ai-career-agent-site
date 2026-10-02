# JOB-003 runbook

## Verification

Run `python scripts/check_job003_package.py`, focused JOB-003 tests, inherited JOB-001/JOB-002/privacy/backup tests, then the full suite. Test upgrade from 0022 and downgrade to 0022 on disposable PostgreSQL.

## Release boundary

Production migration requires separate owner approval and a confirmed recovery point. Do not deploy, migrate Neon, alter provider configuration, or send external notifications from this package. Rollback drops `saved_vacancy_reminders` first and `notification_preferences` second; this deletes reminder data.

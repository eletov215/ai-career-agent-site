AUTH-001 MAIL.RU SMTP SSL/TLS FALLBACK v1.4.15

Baseline: current GitHub archive ai-career-agent-site-main (10).zip.

Production code change:
  config.py
  services/email_delivery.py

New environment switch:
  AUTH_SMTP_USE_SSL=0|1

Transport contract:
  STARTTLS: AUTH_SMTP_USE_TLS=1, AUTH_SMTP_USE_SSL=0
  implicit SSL/TLS: AUTH_SMTP_USE_TLS=0, AUTH_SMTP_USE_SSL=1
  production plaintext: rejected
  both secure flags enabled: rejected

Mail.ru staging profile:
  AUTH_SMTP_HOST=smtp.mail.ru
  AUTH_SMTP_PORT=465
  AUTH_SMTP_USE_TLS=0
  AUTH_SMTP_USE_SSL=1
  AUTH_SMTP_USERNAME=<full Mail.ru address>
  AUTH_EMAIL_FROM=<same full Mail.ru address>
  AUTH_SMTP_PASSWORD=<external app password in Render only>

No migration. Expected database revision remains 20260810_0008.

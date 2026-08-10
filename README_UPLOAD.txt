AUTH-001 SAFARI CSRF HOTFIX v1.4.14

Baseline: current GitHub archive ai-career-agent-site-main (9).zip.

Primary production change:
  routes/auth.py
  Referrer-Policy: no-referrer -> strict-origin

Reason:
  Render Safari logs proved valid auth POSTs were rejected by Flask-WTF strict
  HTTPS CSRF before auth logic because no-referrer suppressed the Referer header.

Security:
  CSRF remains enabled and WTF_CSRF_SSL_STRICT remains true in production.
  strict-origin sends only scheme/host/port, not verification/reset token path/query.

No migration. No new environment variables. SMTP settings remain unchanged.

AUTH-001 GMAIL API HTTPS STAGING CANDIDATE v1.4.16

Baseline: current GitHub archive ai-career-agent-site-main (11).zip.

Primary code changes:
  config.py
  services/email_delivery.py

New backend:
  AUTH_EMAIL_BACKEND=gmail_api

Required Render secrets for Gmail API:
  AUTH_EMAIL_FROM=<authorized Gmail sender>
  AUTH_GMAIL_CLIENT_ID=<secret/config value>
  AUTH_GMAIL_CLIENT_SECRET=<secret>
  AUTH_GMAIL_REFRESH_TOKEN=<secret>
  AUTH_GMAIL_TIMEOUT_SECONDS=8

Transport:
  HTTPS OAuth token exchange
  HTTPS Gmail users.messages.send
  no SMTP port required
  no permanent access token stored

Existing SMTP STARTTLS/implicit SSL backends remain compatible.
No migration: expected schema revision remains 20260810_0008.

Release policy:
  Gmail API is only a staging transport for Render Free.
  Before beta/commercial release move to project-owned domain sender
  (target example noreply@ai-career-agent.ru) with SPF/DKIM/DMARC.

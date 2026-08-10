AUTH-001 candidate v1.4.13

Branch: auth-001-first-party-account
Commit: auth: add first-party account and revocable sessions
Required CI: Verify AUTH-001 first-party account controls
Expected revision: 20260810_0008

Use the complete project ZIP for GitHub Desktop, or overlay the compact
AUTH-001 code patch onto the current main branch.

Production SMTP secrets must be configured only in Render/VPS Environment;
see docs/AUTH001_RUNBOOK.md. Do not upload .env, secrets, databases, dumps,
backups, virtualenv, caches or bytecode.

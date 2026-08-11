AI Career Agent — AUTH-002 candidate v1.4.18

1. Baseline: ai-career-agent-site-main (12).zip from current GitHub main/Render.
2. WSGI remains app:app; do not create app_fixed.py.
3. Candidate migration: 20260811_0009.
4. AUTH-002 makes first-party User the only browser identity.
5. HH/SuperJob connect requires first-party login and state bound to the current server-side auth session.
6. Existing unbound rows are never linked by email; claim requires fresh provider OAuth proof.
7. Tokens remain encrypted; disconnect deletes only current User local credentials and rollback mirror.
8. Upload only after reviewing the full and patch manifests.
9. AUTH-002 remains NEEDS VERIFICATION until GitHub green, Render 0009 and real HH/SJ E2E.

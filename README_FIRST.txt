AI CAREER AGENT — PRIV-001 CANDIDATE v1.4.27

STATUS
- PROF-001: COMPLETE
- PROF-002: COMPLETE
- PROF-003: COMPLETE
- PRIV-001: NEEDS VERIFICATION
- Production revision before deploy: 20260812_0012
- Candidate revision: 20260813_0013
- WSGI: app:app

VERIFIED BASE
- Uploaded source: ai-career-agent-site-main (17).zip
- GitHub ZIP comment: c03c0ea06272dd605673ba17ccbe2f234eb2fe71
- Source ZIP SHA-256: 92c25a79ef51981b91ce8c5f996535bc27b41067b2f4eb79bd33044128ad2e71
- PROF-003 final regression and Render log review were confirmed before PRIV-001 start.

WHAT THIS CANDIDATE ADDS
- /privacy-center owner controls;
- readable ZIP export: manifest.json, data.json and owned resume image assets;
- explicit secret-field omission from export;
- account deletion protected by current password + exact phrase + CSRF + rate limit;
- local HH/SuperJob unified OAuth + legacy credential cleanup before User cascade;
- identifier-free privacy audit table;
- technical retention cleanup CLI/worker;
- migration 20260813_0013 and dedicated CI gate.

TECHNICAL RETENTION DEFAULTS
- pending unverified account: 30 days;
- expired/revoked auth artifact: 30 days;
- identifier-free privacy audit: 180 days;
- cleanup cadence: 24 hours.
These are technical defaults, not a legal-compliance claim; LEGAL-001 owns final policy wording.

CORRECT DEPLOY FLOW
1. Create branch: priv-001-candidate-v1.4.27
2. Upload/extract PATCH ZIP contents preserving paths.
3. Confirm infra/vps/.env.example remains present. Never add a real .env.
4. Open Pull Request to main.
5. Wait for all CI, including Verify PRIV-001 privacy export deletion and retention controls.
6. Merge only when fully green.
7. Verify Render /health/ready current_revision=expected_revision=20260813_0013.
8. Run destructive privacy E2E only with a throwaway account.

Remote provider-side OAuth grant revocation is not implemented/claimed by this package; local credentials are deleted.
Do not commit secrets, personal resume samples, databases, dumps, backups, virtualenv, caches or bytecode.

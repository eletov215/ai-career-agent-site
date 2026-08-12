AI CAREER AGENT — PROF-002 CANDIDATE v1.4.23

STATUS
- PROF-001: COMPLETE
- PROF-002: NEEDS VERIFICATION
- Production revision before deploy: 20260811_0010
- Candidate revision: 20260812_0011
- WSGI: app:app

VERIFIED BASE
- Uploaded source: ai-career-agent-site-main (16).zip
- GitHub main commit in ZIP comment: f5e513f0f992b20305fbef36851ef97576013c86
- Source ZIP SHA-256: 5e411f3dabc024a4adbf6be05d9fa49ce11e5e36407ac2b068aada0dd3109d0d
- Exact match with the last full PROF-001 hotfix snapshot before edits.

WHAT THIS CANDIDATE ADDS
Text PDF -> bounded deterministic proposal -> editable review -> explicit owner confirmation -> immutable PROF-001 version with aggregate provenance.

No upload bytes, raw resume text, filename or unconfirmed proposal are persisted. OCR, DOC/DOCX, AI parsing, provider resume import and persisted drafts are excluded.

CORRECT DEPLOY FLOW
1. Create branch: prof-002-candidate-v1.4.23
2. Upload/extract the PATCH ZIP contents preserving paths.
3. Open Pull Request to main.
4. Wait for all CI, including Verify PROF-002 resume import review controls.
5. Merge only when green.
6. Verify Render /health/ready current_revision=expected_revision=20260812_0011.
7. Run PROF-002 positive/negative/privacy/owner/stale/restart/mobile E2E.

Do not commit .env, tokens, resume samples with personal data, databases, dumps, backups, virtualenv, caches or bytecode.

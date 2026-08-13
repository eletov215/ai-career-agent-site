AI CAREER AGENT — PROF-003 CANDIDATE v1.4.25

STATUS
- PROF-001: COMPLETE
- PROF-002: COMPLETE
- PROF-003: NEEDS VERIFICATION
- Production revision before deploy: 20260812_0011
- Candidate revision: 20260812_0012
- WSGI: app:app

VERIFIED BASE
- Uploaded source: ai-career-agent-site-main (16).zip
- GitHub ZIP comment: 427b2726edd078993a3c26985e17713cf2e76c9e
- Source ZIP SHA-256: ddd4d61f0afbf3351c0623506fc9e35aca757e0536716b4015349abc96e40864
- Functional code matches the PROF-002 COMPLETE + upload-limit hotfix r2 snapshot.
- Eleven stale repository documentation files were synchronized with canonical v1.4.24 before PROF-003 changes.

WHAT THIS CANDIDATE ADDS
- owner-scoped multiple ResumeDraft documents;
- server autosave with optimistic revision conflict protection;
- immutable checkpoint/export/restore ResumeVersion history;
- owner/draft-scoped private photo and university-logo assets;
- browser PDF export metadata tied to the exact immutable version;
- one-time migration of the former localStorage draft, after which PostgreSQL is authoritative;
- optional one-way seed from confirmed PROF-001 facts without reverse auto-write.

CORRECT DEPLOY FLOW
1. Create branch: prof-003-candidate-v1.4.25
2. Upload/extract the PATCH ZIP contents preserving paths.
3. Confirm infra/vps/.env.example remains present. Never add a real .env.
4. Open Pull Request to main.
5. Wait for all CI, including Verify PROF-003 server resume draft and version controls.
6. Merge only when green.
7. Verify Render /health/ready current_revision=expected_revision=20260812_0012.
8. Run owner/autosave/version/restore/asset/export/restart/mobile/regression E2E.

No new environment variables are required.
Do not commit real secrets, personal resume samples, databases, dumps, backups, virtualenv, caches or bytecode.

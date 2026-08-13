PROF-003 PATCH UPLOAD INSTRUCTIONS — v1.4.25

Use a separate GitHub branch. Do not upload the ZIP file itself into the repository.

1. Create branch from current main:
   prof-003-candidate-v1.4.25

2. Extract:
   ai-career-agent-site-main-patch-prof-003-candidate-v1.4.25.zip

3. Upload the extracted files/folders into the repository root with paths preserved.
   Examples:
   services/resume_drafts.py
   routes/resume_drafts.py
   migrations/versions/20260812_0012_resume_drafts_versions.py
   templates/resumes/library.html
   tests/test_prof003_migration.py

4. Confirm GitHub shows source files at repository root, not one nested project folder and not the ZIP itself.

5. Confirm infra/vps/.env.example is still present. It is a required secret-free placeholder. Never commit a real .env.

6. Commit and open Pull Request to main.

7. Required green checks include:
   - Verify PROF-003 server resume draft and version controls
   - Verify PROF-002 resume import review controls
   - Verify PROF-001 structured career profile controls
   - Verify PostgreSQL migrations
   - Run PostgreSQL integration test
   - Verify AUTH-001 / AUTH-002 regressions
   - Verify PostgreSQL encrypted backup and restore
   - Run tests
   - Docker/Compose runtime smoke

8. After merge, Render must report revision 20260812_0012 and status ok before production E2E.

No new environment variables are required.

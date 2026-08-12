PROF-002 PATCH UPLOAD INSTRUCTIONS

Use a separate GitHub branch. Do not upload the ZIP file itself into the repository.

1. Create branch from current main:
   prof-002-candidate-v1.4.23

2. Extract:
   ai-career-agent-site-main-patch-prof-002-candidate-v1.4.23.zip

3. Upload the extracted files/folders into the repository root with paths preserved.
   Examples:
   services/resume_import.py
   routes/profile.py
   migrations/versions/20260812_0011_profile_import_provenance.py
   templates/profile/import_upload.html

4. Confirm GitHub shows modified/new source files, not one nested project folder and not the ZIP itself.

5. Commit and open Pull Request to main.

6. Required green checks include:
   - Verify PROF-002 resume import review controls
   - Verify PROF-001 structured career profile controls
   - Verify PostgreSQL migrations
   - Run PostgreSQL integration test
   - Verify AUTH-001 / AUTH-002 regressions
   - Verify PostgreSQL encrypted backup and restore
   - Run tests
   - Docker/Compose runtime smoke

7. After merge, Render must report revision 20260812_0011 and status ok before production E2E.

No new environment variables are required.

PRIV-001 PATCH UPLOAD INSTRUCTIONS — v1.4.27

Use a separate GitHub branch. Do not upload the ZIP file itself into the repository.

1. Create branch from current main:
   priv-001-candidate-v1.4.27

2. Extract:
   ai-career-agent-site-main-patch-priv-001-candidate-v1.4.27.zip

3. Upload the extracted files/folders into the repository root with paths preserved.
   Examples:
   services/privacy.py
   repositories/privacy.py
   routes/privacy_controls.py
   migrations/versions/20260813_0013_privacy_controls.py
   templates/privacy/center.html
   tests/test_priv001_migration.py

4. Confirm GitHub shows source files at repository root, not one nested project folder and not the ZIP itself.

5. Confirm infra/vps/.env.example is still present. Never commit a real .env.

6. Commit and open Pull Request to main.

7. Required green checks include:
   - Verify PRIV-001 privacy export deletion and retention controls
   - Verify PROF-003 server resume draft and version controls
   - Verify PROF-002 resume import review controls
   - Verify PROF-001 structured career profile controls
   - Verify PostgreSQL migrations
   - Run PostgreSQL integration test
   - Verify AUTH-001 / AUTH-002 regressions
   - Verify PostgreSQL encrypted backup and restore
   - Run tests
   - Docker/Compose runtime smoke

8. After merge, Render must report revision 20260813_0013 and status ok before production E2E.

9. Destructive account-delete E2E must use a throwaway verified account. Confirm wrong phrase/password cannot delete; export is readable and secret-free; exact phrase + current password deletes local user data/credentials; old login fails; audit/logs contain aggregate data only.

No new secret is required. PRIVACY_* values have non-secret defaults.
Remote provider-side OAuth grant revoke is outside the verified scope; local credential erasure is the current contract.

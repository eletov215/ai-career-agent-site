AI Career Agent — PROF-001 candidate v1.4.20

1. Baseline: ai-career-agent-site-main (14).zip from current GitHub main/Render.
2. WSGI remains app:app; app_fixed.py is not used.
3. Candidate migration: 20260811_0010.
4. PROF-001 adds one owner-scoped structured career profile per first-party User.
5. Incomplete profiles are allowed; explicit manual save is the confirmation boundary.
6. Every material save creates an immutable full snapshot; unchanged save creates no duplicate version.
7. Stale editors fail closed through expected_version, row locking and database constraints.
8. Upload the PATCH to a separate branch and open a Pull Request; do not push the candidate directly to main.
9. PROF-001 remains NEEDS VERIFICATION until Pull Request CI, Render 0010 and owner/version/restart E2E are green.

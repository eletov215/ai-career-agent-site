AI Career Agent — SYNC-002 code patch v1.4.3

Base: ai-career-agent-site-main (5).zip / current GitHub main after SYNC-001.
Copy the contents of this archive to the repository root, preserving paths and dotfiles.

Package status: NEEDS VERIFICATION.
Do not merge until GitHub Actions is fully green, including:
- Verify SYNC-002 incremental freshness and cleanup controls
- PostgreSQL migrations and integration
- SEC/OPS/INFRA checks
- full pytest

Render Start Command remains:
python scripts/manage_db.py upgrade && python scripts/start_runtime.py

Expected candidate Alembic revision after deploy: 20260807_0004

AUTH-001 CI FIX 1

Replace only:
  tests/test_routes.py

Reason:
The SEC-001 regression fixture used a hard-coded published_at=2026-08-03.
The vacancy search defaults to period=7 days, so on 2026-08-10 the fixture
became older than the active search window and was correctly filtered out.
The fixture now uses the current UTC timestamp. The SuperJob route fixture was
updated the same way to prevent the same future time-dependent failure.

No production code, database migration, environment variables or Render settings change.

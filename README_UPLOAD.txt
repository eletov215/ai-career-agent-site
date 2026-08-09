SEARCH-002 verification hotfix: aggregate dedup status endpoint.

Changed files:
- app.py
- observability.py
- tests/test_observability.py
- tests/test_routes.py
- docs/CHANGELOG.md
- docs/SEARCH002_VERIFICATION_STATUS.md

After deploy:
1. Run any normal vacancy search on /vacancies/internal.
2. Open /health/search-dedup in the browser.
3. Read dedup.stats.cross_source_duplicate_count and dedup.stats.cross_source_groups.

The endpoint does not call vacancy providers and does not store/expose keyword, region, salary, credentials or tokens.

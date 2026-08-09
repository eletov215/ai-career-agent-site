SEARCH-003 latency hotfix 1 on top of candidate revision 20260809_0007.

Problem found on Render:
The first vacancy search could appear to load indefinitely because SEARCH-003 used the provider/cache page size (60) as the logical UI page size, could synchronously run up to three provider rounds, and persisted snapshot candidates/items with too many row-by-row database operations.

Fix:
- SEARCH_PAGE_SIZE=20 separates the UI page from provider/cache page size.
- SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST default is 1.
- candidate persistence uses one existing-identity lookup plus bulk insert per provider page.
- materialized items use bulk insert.
- committing a served page updates only snapshot metadata instead of rewriting the same item rows again.
- migration does not change; expected Render revision remains 20260809_0007.

Recommended branch:
search-003-stable-pagination

Recommended commit:
fix: bound SEARCH-003 request latency

Expected GitHub Actions step:
Verify SEARCH-003 stable pagination and totals controls

Production verification after deploy:
1. /health/ready remains current_revision=expected_revision=20260809_0007.
2. Run a broad vacancy search; page 0 should return instead of remaining in an endless browser load.
3. URL must include snapshot=<uuid>.
4. Open page 2 and return to page 1; snapshot stays the same and cards do not overlap.
5. Open /health/search-pagination?snapshot=<uuid>.

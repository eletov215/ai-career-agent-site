SEARCH-003 candidate: persistent bounded search snapshots, deterministic global sorting and honest total semantics.

Recommended branch:
search-003-stable-pagination

Recommended commit:
search: add persistent stable pagination and honest totals

Important files:
- services/search_aggregation.py
- repositories/search_snapshots.py
- models/search_snapshot.py
- migrations/versions/20260809_0007_stable_search_snapshots.py
- tests/test_search_pagination.py
- .github/workflows/ci.yml

Expected GitHub Actions step:
Verify SEARCH-003 stable pagination and totals controls

Expected Render revision after merge:
20260809_0007

Production verification:
1. Open /vacancies/internal and run a broad multi-source search.
2. Open page 2 with the generated snapshot parameter.
3. Return to page 1 using the same snapshot; the cards and order must be unchanged.
4. Adjacent pages must not contain the same vacancy identity.
5. Open /health/search-pagination?snapshot=<snapshot-id>.
6. Confirm known_unique_total/provider_reported_total/total_is_exact/bounded, per-provider cursor state and candidate_counts_by_source coverage.

The snapshot stores only a SHA-256 query fingerprint and bounded provider/result data. The public verification endpoint does not expose keyword, region, salary, credentials or provider payloads.

SEARCH-001 CI fix 1

Replace tests/test_routes.py in the current SEARCH-001 branch with the file from this archive.
No production code or database migration changes are included.
Reason: the SEC-001 provider-failure isolation test used keyword=python while its mocked successful vacancy did not contain that keyword. SEARCH-001 now applies canonical aggregation filters, so the fixture must satisfy the query it is testing.

SEARCH-002 — загрузка candidate

Полный архив загружается в отдельную ветку search-002-cross-source-dedup с заменой файлов.
Проверь наличие:
- .github/workflows/ci.yml
- migrations/versions/20260809_0006_cross_source_dedup_keys.py
- services/vacancy_deduplication.py
- tests/test_search_deduplication.py
- docs/SEARCH002_*.md

Не объединять Pull Request до зелёного шага Verify SEARCH-002 cross-source deduplication controls.


SuperJob public search hotfix:
- services/superjob_provider.py supports app-level vacancy search without user OAuth
- app.py exposes SuperJob as a search source when app credentials are configured
- templates/vacancies_unified.html labels it as available without login
- tests cover anonymous SuperJob search

After upload, wait for green CI and verify HH + SuperJob search on Render.

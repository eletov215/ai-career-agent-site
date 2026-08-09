SEARCH-002 — загрузка candidate

Полный архив загружается в отдельную ветку search-002-cross-source-dedup с заменой файлов.
Проверь наличие:
- .github/workflows/ci.yml
- migrations/versions/20260809_0006_cross_source_dedup_keys.py
- services/vacancy_deduplication.py
- tests/test_search_deduplication.py
- docs/SEARCH002_*.md

Не объединять Pull Request до зелёного шага Verify SEARCH-002 cross-source deduplication controls.

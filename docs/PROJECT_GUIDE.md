# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Более новый ZIP текущего чата становится рабочей основой.
3. Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4. Главный entrypoint — `app.py`, WSGI — `app:app`; `app_fixed.py` не используется.

## 2. Текущий пакет

```text
SEARCH-003 — НУЖНА ПРОВЕРКА
branch: search-003-stable-pagination
commit: search: add persistent stable pagination and honest totals
candidate revision: 20260809_0007
```

## 3. Обязательный цикл

```text
актуальный ZIP + canonical docs
→ один package ID
→ inventory/risks/rollback
→ code + tests + migrations
→ branch/PR
→ green GitHub Actions
→ Render/API/E2E smoke
→ final status/docs
```

## 4. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra migrations
python -m pytest -q
python -m alembic check
```

GitHub Actions должен отдельно выполнить `Verify SEARCH-003 stable pagination and totals controls`, PostgreSQL migration/integration, backup/restore, Docker build/runtime и полный pytest.

## 5. SEARCH-003 production verification

1. `/health/ready` показывает revision `20260809_0007`.
2. Выполнить широкий multi-source search.
3. Проверить page 0 → page 1 → page 0 с одним `snapshot` ID.
4. На соседних страницах нет одинаковых stable identities.
5. Возврат на page 0 воспроизводит прежний порядок.
6. `/health/search-pagination?snapshot=<uuid>` показывает honest totals, per-source cursors и candidate coverage без query text/credentials.
7. Каждый non-terminal provider покрывает required depth для committed boundary либо отмечен exhausted/bounded.

## 6. Неприкосновенные правила

- `.env`, credentials, databases, dumps, backups, virtualenv, caches и bytecode не включаются в ZIP/GitHub.
- Реальные APIs в CI mocked.
- Production schema меняет только Alembic.
- Snapshot exact total не добывается массовым synchronous upstream scan.
- SEARCH-003 не меняет SEARCH-002 thresholds, OAuth strategy и route redesign SEARCH-004.

## 7. Rollback

Application revert без очистки vacancy cache. Additive `0007` может остаться; downgrade до `0006` — только после verified backup и deployment совместимого старого кода.

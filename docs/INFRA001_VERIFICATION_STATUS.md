# INFRA-001 - статус реализации и проверки

| Поле | Значение |
|---|---|
| Версия отчёта | 1.0 |
| Дата | 06 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА НА VPS |
| Кодовая основа | `ai-career-agent-site-main (3).zip` |

## 1. Реализовано

| Область | Статус |
|---|:---:|
| Runtime Docker image | ГОТОВО |
| OPS PostgreSQL 17 image | ГОТОВО |
| Docker Compose stack | ГОТОВО |
| One-shot migrations | ГОТОВО |
| Private DB network | ГОТОВО |
| Caddy TLS profile | ГОТОВО |
| VPS environment template | ГОТОВО |
| Infrastructure probe | ГОТОВО |
| Provider decision record | ГОТОВО |
| Unit/manifest tests | ГОТОВО |
| CI container build/smoke | ТРЕБУЕТ GITHUB ACTIONS |
| Real VPS deploy | НЕ ВЫПОЛНЕНО |
| РФ/РБ network matrix | НЕ ВЫПОЛНЕНО |
| Production backup/restore | НЕ ВЫПОЛНЕНО |

## 2. Изменённые файлы

```text
Dockerfile
.dockerignore
.gitignore
compose.yaml
infra/gunicorn.conf.py
infra/vps/Caddyfile
infra/vps/.env.example
infra/vps/compose.test.env
scripts/infra_probe.py
scripts/infra_manifest_check.py
scripts/infra_container_smoke.sh
tests/test_infra_probe.py
tests/test_infra_manifests.py
.github/workflows/ci.yml
requirements-dev.txt
docs/* INFRA and canonical sources
```

## 3. Локальные доказательства

| Проверка | Результат |
|---|---|
| Repository hygiene | ПРОЙДЕНО |
| Compileall | ПРОЙДЕНО |
| Full pytest | `103 passed, 6 skipped` |
| INFRA tests | `12 passed` |
| SQLite migrations | `20260804_0002` |
| Alembic check | ПРОЙДЕНО |
| Manifest validator | `ok: true` |
| CI YAML parsing | 20 steps, корректно |
| Shell syntax | ПРОЙДЕНО |
| Docker build/smoke | Не запускался локально: Docker CLI отсутствует; выполняется в GitHub Actions |

## 4. GitHub критерии

```text
Verify INFRA-001 manifests and probe tooling
Validate INFRA-001 Docker Compose configuration
Build INFRA-001 container targets
Smoke-test INFRA-001 runtime image
Run tests
```

## 5. VPS критерии

- test URL без VPN доступен из РФ/РБ;
- TLS валиден;
- app live/ready/home - 200;
- Yandex AI edge и Reed transport доступны;
- search/PDF/security smoke проходят;
- production backup restored in isolated DB;
- provider choice documented.

## 6. Следующее действие

После зелёного CI создать тестовый VPS у Timeweb Cloud как первого кандидата.

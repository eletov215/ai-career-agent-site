# INFRA-PREP-001 / INFRA-001 — статус

| Поле | Значение |
|---|---|
| Версия отчёта | 1.1 |
| Дата | 07 августа 2026 |
| INFRA-PREP-001 | ВЫПОЛНЕНО |
| INFRA-001 real VPS | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |
| Канонический план | PLAN_CURRENT 1.4.1 |

## 1. INFRA-PREP-001 — выполнено

| Область | Статус |
|---|:---:|
| Runtime Docker image | ПРОЙДЕНО CI |
| OPS PostgreSQL 17 image | ПРОЙДЕНО CI |
| Docker Compose stack | ПРОЙДЕНО CI |
| One-shot migrations | ПРОЙДЕНО CI |
| Private DB network | ПРОЙДЕНО |
| Caddy TLS profile | ПРОЙДЕНО manifest tests |
| VPS environment template | ПРОЙДЕНО |
| Infrastructure probe | ПРОЙДЕНО |
| Provider decision template | ГОТОВО |
| Container build/runtime smoke | ПРОЙДЕНО GitHub Actions |
| External sync-worker profile | ДОБАВЛЕНО SYNC-001, ожидает regression CI |

## 2. Классификация PLAN_CURRENT 1.4.0+

Кодовая container/probe часть прежнего INFRA-001 выделена в завершённый `INFRA-PREP-001`. Это позволяет продолжать hosting-independent functional development без аренды простаивающего VPS.

`INFRA-001` теперь означает только реальную аренду и полевой тест VPS перед beta/production.

## 3. Real INFRA-001 — отложено

Будущие критерии:

- public IPv4 и временный TLS hostname;
- доступность из минимум двух сетей РФ и одной сети РБ;
- live/ready/home/search/PDF/security smoke;
- Yandex AI и Reed transport с exact source IP;
- latency/cost/SLA/backup assessment;
- provider decision record.

## 4. SYNC-001 изменение container baseline

Compose получил отдельный service:

```text
sync-worker (profile: sync)
```

Он не публикует ports, работает в private backend network и запускает `scripts/trudvsem_sync_worker.py`. Web service остаётся Gunicorn-only. Render free staging использует sibling-process supervisor.

## 5. Следующее действие

Не создавать VPS сейчас. Сначала завершить SYNC-001 verification и функциональные MVP packages. Real INFRA-001 выполняется в отдельном предрелизном окне до beta, а не в день запуска.

## 6. Журнал

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 06.08.2026 | INFRA toolkit ожидал real VPS verification |
| 1.1 | 07.08.2026 | Toolkit классифицирован как completed INFRA-PREP; real VPS test отложен; добавлен SYNC worker profile |

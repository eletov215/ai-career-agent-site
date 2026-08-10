# AI Career Agent — аудит источников v1.4.11

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.11 |
| Дата | 10 августа 2026 |
| Проверяемый пакет | SEARCH-004 candidate implementation |
| Рабочий источник кода | `ai-career-agent-site-main (14).zip` из актуального GitHub `main` |
| Канонический план до обновления | PLAN_CURRENT 1.4.10 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.24 |
| Результат | SEARCH-004 реализован локально; требуется GitHub/Render verification |

## 1. Контрольный статус

SEARCH-003 остаётся ВЫПОЛНЕНО. SEARCH-004 имеет статус НУЖНА ПРОВЕРКА. Production schema остаётся `20260809_0007`; migration не добавлялась. DOC-STD-001 v1.1 остаётся обязательным.

## 2. Проверка актуального источника кода

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены |
| Database | PostgreSQL/Alembic revision `20260809_0007`; schema не менялась |
| Canonical route | `/vacancies` обслуживает unified search UI |
| Legacy compatibility | `/vacancies/internal` -> permanent `308`, raw query сохраняется |
| SEARCH-003 | `snapshot`/`page` query semantics не меняются |
| Source states | `services/source_status.py` с 5 safe public states |
| Trudvsem | Явно cache-based, не маскируется под live provider |
| Generated links | Forms, pagination, navbar/footer/home CTA используют `/vacancies` |
| Public safety | Нет exception bodies, tokens, credentials или env variable names |
| Prohibited artifacts | `.env`, DB/dump/backup/venv/cache/bytecode должны отсутствовать в release ZIP |

## 3. Реализованный scope SEARCH-004

- canonical GET `/vacancies`;
- permanent method-preserving compatibility redirect со старого route с сохранением repeated `source`, filters, `snapshot`, `page`;
- canonical meta tag;
- safe state contract `available`, `cached`, `degraded`, `auth_required`, `temporarily_unavailable`;
- neutral failure copy для HH/SuperJob/Reed;
- cache age/refresh state для Trudvsem без raw worker errors;
- source state badges в main и compact UI;
- dedicated GitHub Actions gate;
- route, template, source-state и pagination regressions.

Admin telemetry, новые providers, OAuth redesign, AI matching и card redesign не входят в пакет.

Плановая оговорка: в PLAN_CURRENT 1.4.10 таблица этапа перечисляла SEARCH-005 рядом с SEARCH-004, но обязательная последовательность раздела 15.1 и зависимость SEARCH-005 от AUTH-001 определяют `AUTH-001` как следующий обязательный пакет после закрытия SEARCH-004. SEARCH-005 остаётся после account/profile/privacy foundation.

## 4. Локальные доказательства

```text
Python compileall                         passed
Jinja parse all templates                 passed
Focused source-state tests                6 passed
Full available pytest                     193 passed, 6 skipped
```

Шесть skips относятся к Flask/Psycopg/PostgreSQL runtime scenarios текущей изолированной среды. Они не объявляются пройденными до GitHub Actions.

## 5. Verification gate

1. GitHub Actions полностью зелёный, включая `Verify SEARCH-004 canonical route and source-state controls`.
2. Render `/health/ready`: `status=ok`, current/expected revision `20260809_0007`.
3. `/vacancies` возвращает 200 и полный search UI.
4. `/vacancies/internal?<query>` возвращает 308 на `/vacancies` с тем же raw query, UUID snapshot и page.
5. Generated HTML/pagination не содержит `/vacancies/internal`.
6. Trudvsem показывается как cached/degraded; live provider failure не ломает общую выдачу.
7. Public copy не раскрывает credentials, exception bodies или имена environment variables.

## 6. Ограничения и риски

- Redirect использует permanent method-preserving `308`; no-store защищает verification/rollback window от stale cache.
- Source state — пользовательский status, а не SLA/administrative telemetry. Подробный центр относится к SEARCH-005.
- SEARCH-003 snapshot schema/algorithm не менялись.

## 7. Rollback

Application revert. Database downgrade не нужен; revision `0007` сохраняется. На rollback-окне legacy URL должен оставаться доступным или redirect-safe.

## 8. Следующее действие

```text
SEARCH-004 CANDIDATE
-> green GitHub CI
-> Render canonical/redirect/source-state smoke
-> SEARCH-004 COMPLETE
-> AUTH-001 START
```

## 9. Новые канонические версии

```text
PLAN_CURRENT 1.4.11
PROJECT_PASSPORT 2.25
SOURCE_AUDIT 1.4.11
SEARCH004_IMPLEMENTATION 1.0
SEARCH004_VERIFICATION_STATUS 1.0
SEARCH004_RUNBOOK 1.0
SEARCH004_SOURCE_STATE_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.10 | 09.08.2026 | SEARCH-003 final verification; SEARCH-004 prepared. |
| 1.4.11 | 10.08.2026 | SEARCH-004 candidate: canonical route, compatibility redirect, safe source states и local verification. |

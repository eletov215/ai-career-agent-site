# AI Career Agent — дорожная карта

> Каноническая подробная версия находится в `AI_Career_Agent_PLAN_CURRENT`. Этот файл — краткое инженерное представление для репозитория.

## Этап 1. Стабилизация и безопасная основа

- [x] `FND-001` — базовые тесты и CI.
- [x] `FND-002` — конфигурация development/test/production.
- [x] `DATA-001` — PostgreSQL и Alembic; production persistence подтверждена.
- [x] `DATA-002` — доменные модели и repository layer; migration 0002, CI, Render и restart persistence подтверждены.
- [ ] `SEC-001` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА НА RENDER**: основная production-проверка прошла; rate-limit key исправлен для Cloudflare/Render, нужен зелёный CI и контролируемый `429` на probe endpoint.
- [ ] `OPS-001` — **НУЖНА ПРОВЕРКА**: structured logs, request IDs, metrics, alerts, live/readiness и encrypted backup/restore реализованы; нужен CI/production verification.
- [ ] `DOC-001` — периодическая сверка документов и фактического кода.

## Этап 2. Качественный поиск

- [ ] `SYNC-001` — вынести Trudvsem из web-процесса.
- [ ] `SYNC-002` — инкрементальная загрузка и cleanup.
- [ ] `SEARCH-001` — каноническая схема вакансии.
- [ ] `SEARCH-002` — межисточниковая дедупликация на основе `Vacancy` + `VacancySourceRecord`.
- [ ] `SEARCH-003` — стабильная pagination/sort/total.
- [ ] `SEARCH-004` — canonical `/vacancies`.
- [ ] `SEARCH-005` — защищённый центр состояния источников.

## Этап 3. Пользователь и профиль

- [ ] `AUTH-001` — аккаунт AI Career Agent на основе `User`.
- [ ] `AUTH-002` — привязка unified `OAuthConnection` к пользователю.
- [ ] `PROF-001` — структурированный карьерный профиль.
- [ ] `PROF-002` — импорт PDF в подтверждаемый профиль.
- [ ] `PROF-003` — серверные черновики/версии.
- [ ] `PRIV-001` — export/delete/retention.

## Этап 4. Реальный AI-контур

- [ ] `AI-BENCH-001` — benchmark Yandex AI Studio/Alice AI.
- [ ] `AI-PROVIDER-001` — provider/geography/privacy/cost/fallback decision.
- [ ] `AI-001` — независимый AI provider layer.
- [ ] `AI-002` — анализ резюме.
- [ ] `AI-003` — адаптивное интервью.
- [ ] `AI-004` — объяснимый matching.
- [ ] `AI-005` — сопроводительные письма.
- [ ] `AI-006` — evals и защита от галлюцинаций.

## Этап 5. Вакансии и отклики

- [ ] `JOB-001` — серверные сохранённые вакансии.
- [ ] `JOB-002` — трекер откликов.
- [ ] `JOB-003` — добровольные уведомления.
- [ ] `JOB-004` — личная аналитика.

## Этап 6. Коммерческий запуск, VPS, домен и миграция

- [ ] `INFRA-001` — выбор и технический тест российского VPS из РФ/РБ.
- [ ] `REED-COMPAT-001` — API smoke и договорная проверка Reed с точного VPS.
- [ ] `HOST-001` — production VPS, Docker/Compose, proxy, PostgreSQL, TLS, deploy.
- [ ] `DOMAIN-001` — собственный домен, DNS, TLS, `PUBLIC_BASE_URL`, OAuth callbacks.
- [ ] `MIG-001` — перенос PostgreSQL/production с Render с rollback.
- [ ] `OPS-002` — эксплуатация VPS.
- [ ] `PERF-001` — frontend/assets.
- [ ] `A11Y-001` — доступность.
- [ ] `LEGAL-001` — legal/consent до публичного AI.
- [ ] `ANL-001` — продуктовая аналитика без пользовательского текста.
- [ ] `REL-001` — предрелизная проверка.
- [ ] `BILL-001` — тарифы; отложено.
- [ ] `SRC-001` — новые источники; отложено.

## Трассировка DOMAIN-001

`DOMAIN-001` не потерян. В стратегии 1.3.x он выполняется после `HOST-001` и до `MIG-001`, поэтому пользовательский адрес не зависит от конкретного VPS.

## Ближайшая последовательность

```text
SEC-001 rate-limit recheck
-> OPS-001 verification
-> INFRA-001
-> AI-BENCH-001
-> REED-COMPAT-001
-> AI-PROVIDER-001
-> HOST-001
-> DOMAIN-001
-> MIG-001
```

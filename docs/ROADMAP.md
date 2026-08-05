# AI Career Agent — дорожная карта

> Каноническая подробная версия находится в `AI_Career_Agent_PLAN_CURRENT`. Этот файл — краткое инженерное представление для репозитория.

## Этап 1. Стабилизация и безопасная основа

- [x] `FND-001` — базовые тесты и CI.
- [x] `FND-002` — конфигурация development/test/production.
- [x] `DATA-001` — PostgreSQL и Alembic; production persistence подтверждена.
- [x] `DATA-002` — доменные модели и repository layer; migration 0002, CI, Render и restart persistence подтверждены.
- [ ] `SEC-001` — **НУЖНА ПРОВЕРКА**: код CSRF/cookies/rate limits/headers/request limits/technical endpoints подготовлен; требуются GitHub Actions и Render smoke.
- [ ] `OPS-001` — structured logs, error monitoring, backup/restore.
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

## Этап 6. Коммерческий запуск, домен и hosting

- [ ] `DOMAIN-001` — собственный домен, DNS, TLS, `PUBLIC_BASE_URL`, OAuth callbacks.
- [ ] `INFRA-001` — Docker/Compose и portability.
- [ ] `HOST-001` — решение paid Render/VPS по метрикам.
- [ ] `OPS-002` — эксплуатация VPS, только если выбран VPS.
- [ ] `PERF-001` — frontend/assets.
- [ ] `A11Y-001` — доступность.
- [ ] `LEGAL-001` — legal/consent до публичного AI.
- [ ] `ANL-001` — продуктовая аналитика без пользовательского текста.
- [ ] `REL-001` — предрелизная проверка.
- [ ] `BILL-001` — тарифы; отложено.
- [ ] `SRC-001` — новые источники; отложено.

## Трассировка DOMAIN-001

`DOMAIN-001` не был потерян и не интегрирован в DATA-002. Он появился в стратегии `1.1.0`, находится в этапе 6 и намеренно выполняется после security/operations foundation.

## Ближайшая последовательность

```text
SEC-001 verification
-> OPS-001
-> DOMAIN-001
-> SYNC-001 / SEARCH core
-> AUTH / PROFILE
-> AI
```

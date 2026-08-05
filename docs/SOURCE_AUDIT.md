# AI Career Agent — аудит источников

**Дата:** 04 августа 2026  
**Рабочая основа:** `ai-career-agent-site-main (1).zip`  
**Пакет:** DATA-002

## Подтверждено

- Архив соответствует GitHub после завершённого DATA-001.
- Production PostgreSQL/Alembic 0001 подтверждены в плане 1.2.5 и паспорте 2.3.
- Главный файл `app.py`, entrypoint `app:app`.
- CI содержит PostgreSQL 17 migration/integration steps.
- В архиве отсутствуют `.env`, credentials и database snapshots.

## Найденные рассинхронизации

Repository docs внутри ZIP ещё отражали DATA-001 как ожидающий verification, хотя внешний канонический план 1.2.5 уже помечает его выполненным. Документы синхронизированы в DATA-002 candidate.

## DOMAIN-001

Пакет собственного домена не потерян:

- присутствует в `docs/PLAN_CURRENT.md`;
- присутствует в `docs/ROADMAP.md`;
- находится в этапе 6;
- добавлен стратегией версии 1.1.0;
- указан в ближайшей последовательности после `SEC-001` и `OPS-001`.

Он не интегрирован в DATA-002, потому что domain/DNS/TLS/OAuth callback migration требует предварительных security и operations controls. Статус остаётся `ЗАПЛАНИРОВАНО`.

## DATA-002 candidate

Добавлены domain/repository layers, StorageServices, rollback-safe OAuth dual-write и migration 0002. До production verification канонический статус — `НУЖНА ПРОВЕРКА`.

## Канонические источники после текущей работы

1. Новый проектный ZIP DATA-002.
2. `AI_Career_Agent_PLAN_CURRENT` версии 1.2.6.
3. Паспорт проекта версии 2.4.
4. Этот аудит.

Старые дубликаты plan/passport следует удалить после замены.

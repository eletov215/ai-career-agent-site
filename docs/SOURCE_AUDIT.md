# AI Career Agent — аудит источников

**Дата:** 05 августа 2026  
**Рабочая основа:** `ai-career-agent-site-main-14-data-002-completed-v1.2.7.zip`  
**Кандидат:** `ai-career-agent-site-main-15-sec-001-security-v1.2.8.zip`  
**Пакет:** SEC-001 — НУЖНА ПРОВЕРКА

## Подтверждённая база

- FND-001/FND-002 выполнены.
- DATA-001 выполнен: PostgreSQL 17, migration `20260804_0001`, restart persistence.
- DATA-002 выполнен: migration `20260804_0002`, domain/repository layers, persisted sync state и production restart.
- Актуальная database revision до и после SEC-001 должна оставаться `20260804_0002`.

## Реализовано в кандидате SEC-001

- `security.py`: secure cookies, CSRF, rate limiting, request limits, CSP/security headers, neutral errors, diagnostics gate.
- Flask-WTF 1.3.0 и Flask-Limiter 4.1.1.
- POST-only logout, bounded state checked for success/error callbacks, HTTPS-only production OAuth redirect URI, sanitized provider/refresh errors.
- Public `/api/sources/trudvsem/status`; detailed technical endpoints hidden by default.
- PDF page/text/request limits and safe filename handling.
- University-logo SSRF/redirect/body/MIME/signature protection.
- Security config/route/template/SSRF tests and explicit GitHub Actions step.
- `.gitignore` preventing accidental secret/database/cache commits.

## Текущие статусы

- FND-001 — ВЫПОЛНЕНО.
- FND-002 — ВЫПОЛНЕНО.
- DATA-001 — ВЫПОЛНЕНО.
- DATA-002 — ВЫПОЛНЕНО.
- SEC-001 — НУЖНА ПРОВЕРКА.
- OPS-001 — ЗАПЛАНИРОВАНО; следующий после подтверждения SEC-001.
- DOMAIN-001 — ЗАПЛАНИРОВАНО, этап 6, после SEC-001/OPS-001 и до коммерческой beta.

## Что ещё требуется для SEC-001

1. GitHub Actions полностью зелёный, включая `Verify SEC-001 security controls`.
2. Render deploy без startup/import errors.
3. `/health` остаётся на revision `20260804_0002`.
4. Основные страницы, vacancy search, PDF upload и OAuth smoke работают.
5. Public technical URLs закрыты; sanitized source status доступен.
6. CSP/HSTS/cookie/CSRF/rate-limit behavior подтверждены.
7. Render logs не содержат token/provider response body.

## DOMAIN-001

Пакет собственного домена не потерян и не интегрирован в SEC-001. SEC-001 заранее добавляет `TRUSTED_HOSTS`, secure cookie, CSRF и HSTS foundation. Сам `DOMAIN-001` остаётся отдельным инфраструктурным пакетом: регистрация домена, DNS, TLS, `PUBLIC_BASE_URL`, OAuth callbacks и trusted origins.

## Канонические источники после подтверждения загрузки

1. `ai-career-agent-site-main-15-sec-001-security-v1.2.8.zip`.
2. `AI_Career_Agent_PLAN_CURRENT v1.2.8`.
3. Паспорт проекта v2.6.
4. Этот аудит.

Старые candidate-документы 1.2.7/2.5 следует удалить только после загрузки и проверки новых файлов.

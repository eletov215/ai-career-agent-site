# SEC-001 — базовый защитный слой

> Версия кандидата: 05 августа 2026 года  
> Статус: **НУЖНА ПРОВЕРКА**  
> Production entrypoint остаётся `gunicorn app:app`.

## 1. Назначение

SEC-001 закрывает базовые риски до появления собственного аккаунта и реальных пользовательских данных:

- защита state-changing запросов;
- безопасная browser session;
- ограничение частоты и размера запросов;
- нейтральные ошибки;
- закрытие diagnostics/refresh endpoints;
- базовая браузерная политика через security headers;
- дополнительные ограничения PDF и внешнего поиска эмблем.

Пакет не реализует first-party регистрацию, роли администратора, Redis, WAF, antivirus sandbox или отдельный background worker. Эти задачи остаются в AUTH/OPS/SYNC.

## 2. Реализация

### 2.1 Сессия

Production-конфигурация:

```text
SESSION_COOKIE_NAME=aca_session
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
SESSION_REFRESH_EACH_REQUEST=false
SESSION_LIFETIME_SECONDS=43200
```

Cookie остаётся host-only: `SESSION_COOKIE_DOMAIN` намеренно не устанавливается. Production принимает только `SameSite=Lax`, потому что `Strict` не совместим с возвратом браузера из внешнего OAuth-провайдера. После OAuth transient state очищается, а подключённые provider identities переносятся в новую permanent session. OAuth state проверяется и одноразово потребляется как для успешного callback, так и для provider error/cancel, и действует не более 10 минут.

### 2.2 CSRF

`Flask-WTF` включает глобальную защиту для POST/PUT/PATCH/DELETE.

HTML-формы получают hidden `csrf_token`. JavaScript API-запросы передают:

```text
X-CSRF-Token: <token из meta csrf-token>
```

Исключения ограничены двумя machine/non-production endpoints:

- `/sync/trudvsem` — обязательный `X-Sync-Secret`;
- `/trudvsem/refresh` — доступен только вне production и в production возвращает 404.

### 2.3 Rate limiting

`Flask-Limiter` применяет отдельные лимиты к дорогим и чувствительным маршрутам:

| Группа | Пример лимита |
|---|---:|
| OAuth login | 20 / 10 минут |
| OAuth callback | 60 / 10 минут |
| Resume preview | 10 / 10 минут |
| AI Career upload | 6 / 10 минут |
| University logo | 20 / 10 минут |
| Vacancy search | 60 / 5 минут |
| Public source status | 120 / 5 минут |
| Detailed diagnostics | 20–60 / 5 минут |
| Sync webhook | 10 / 5 минут |

Текущий backend — `memory://`. Он приемлем для одного Gunicorn worker. Перед несколькими workers/instances нужно настроить общее Redis-compatible storage через `RATELIMIT_STORAGE_URI`.

### 2.4 Security headers

`security.py` добавляет:

```text
Content-Security-Policy
Strict-Transport-Security (production HTTPS)
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Origin-Agent-Cluster: ?1
X-Permitted-Cross-Domain-Policies: none
X-XSS-Protection: 0
```

CSP запрещает inline event handlers и выполняет scripts только с request nonce. CDN-доступ ограничен текущим `cdnjs.cloudflare.com`; Google Fonts разрешены явно; images ограничены `self`, `data:` и `blob:`.

### 2.5 Ограничения запросов и PDF

```text
MAX_RESUME_UPLOAD_MB=8
MAX_RESUME_PAGES=30
MAX_RESUME_TEXT_CHARACTERS=200000
MAX_FORM_MEMORY_SIZE=262144
MAX_FORM_PARTS=32
```

- upload routes допускают multipart overhead, но отдельно отклоняют PDF больше установленного file limit;
- остальные unsafe requests ограничены 256 KiB;
- university-logo JSON ограничен 32 KiB;
- PDF проверяется по signature, page count и объёму извлечённого текста;
- filename нормализуется через `secure_filename` и не используется как filesystem path.

### 2.6 Diagnostics и технические endpoints

Production defaults:

```text
DEBUG_DIAGNOSTICS=0
DEBUG_HH=0
```

Закрытые маршруты возвращают 404 без правильной конфигурации и заголовка:

```text
/debug/hh
/debug/trudvsem
/trudvsem/status
```

Для временной диагностики нужны:

```text
DEBUG_DIAGNOSTICS=1
DIAGNOSTICS_SECRET=<случайное длинное значение>
X-Diagnostics-Secret: <то же значение>
```

Не передавайте diagnostics secret в query string, screenshot, issue или лог. Public UI использует только:

```text
/api/sources/trudvsem/status
```

Он не возвращает `last_error`, `persisted_run`, internal cursor или credentials.

### 2.7 Нейтральные ошибки и логи

Пользователю не отражаются OAuth/provider exception strings, response bodies и upstream diagnostics. 400/404/405/413/429/500 возвращают краткий русский текст. Подробности сохраняются только в server logs, причём HH logs больше не пишут response body, token или полный набор headers.

### 2.8 University-logo SSRF baseline

Resolver:

- принимает только HTTP/HTTPS;
- запрещает credentials и нестандартные ports;
- отклоняет localhost/private/non-global IP;
- проверяет каждый redirect вручную;
- ограничивает число redirects и размер HTML/image ответа;
- не принимает SVG;
- проверяет image signature и declared MIME type.

## 3. Конфигурация

### Новых обязательных переменных для обычного deploy нет

Без дополнительных настроек production автоматически включает secure cookie, CSRF, limits и headers.

### Опциональные переменные

```text
SESSION_COOKIE_SECURE
SESSION_COOKIE_SAMESITE
SESSION_LIFETIME_SECONDS
CSRF_ENABLED
CSRF_TIME_LIMIT_SECONDS
RATE_LIMIT_ENABLED
RATELIMIT_STORAGE_URI
TRUSTED_HOSTS
TRUST_PROXY_HEADERS
SECURITY_HEADERS_ENABLED
HSTS_SECONDS
MAX_FORM_MEMORY_SIZE
MAX_FORM_PARTS
MAX_RESUME_PAGES
MAX_RESUME_TEXT_CHARACTERS
DEBUG_DIAGNOSTICS
DIAGNOSTICS_SECRET
```

Production не запускается, если явно отключены `SESSION_COOKIE_SECURE`, `CSRF_ENABLED`, `RATE_LIMIT_ENABLED` или `SECURITY_HEADERS_ENABLED`, если выбран `SameSite=Strict`, либо если OAuth callback URL не использует HTTPS/содержит credentials или fragment.

`TRUSTED_HOSTS` автоматически дополняется `RENDER_EXTERNAL_HOSTNAME` и hostname из HH/SuperJob redirect URI. При DOMAIN-001 в список нужно добавить выбранный коммерческий hostname.

## 4. Проверка GitHub Actions

Ожидаемый отдельный шаг:

```text
Verify SEC-001 security controls
```

Он проверяет:

- production/test config;
- CSRF forms/API;
- rate limits;
- cookie flags;
- CSP nonce и template contract;
- neutral errors;
- hidden diagnostics;
- sanitized public source status;
- university-logo SSRF/redirect/MIME/size rules;
- startup modes, HTTPS redirect URI validation and OAuth error-state handling.

Полный pytest и PostgreSQL integration tests должны оставаться зелёными.

## 5. Production smoke после merge

1. `/health` — HTTP 200, revision остаётся `20260804_0002`.
2. Главная, AI Career, resume builder и vacancies открываются.
3. PDF upload с корректным token проходит; запрос без token получает neutral 400.
4. Одиннадцатый быстрый preview request получает 429 в контролируемом тесте, обычное использование не блокируется.
5. `/debug/hh`, `/debug/trudvsem`, `/trudvsem/status`, `/trudvsem/refresh` недоступны публично.
6. `/api/sources/trudvsem/status` остаётся доступен и не содержит raw error.
7. Logout работает POST-form, GET `/logout` возвращает 405.
8. Response headers содержат CSP, HSTS, nosniff, DENY и Referrer-Policy.
9. OAuth HH/SuperJob callback проходит с действительным state; provider error detail не отражается пользователю.
10. Render logs не содержат tokens, response bodies или циклических рестартов.

## 6. Rollback

SEC-001 не добавляет database migration. Для отката достаточно вернуть application commit и redeploy. PostgreSQL schema revision остаётся `20260804_0002`.

При rollback старый GET `/logout` и публичные technical endpoints вернут прежнее поведение, поэтому откат следует использовать только для аварийного восстановления и затем исправить первопричину.

## 7. Известные ограничения

- memory rate-limit backend не координируется между несколькими processes/instances;
- CSP пока допускает inline styles из-за существующей разметки;
- PDF обрабатывается внутри web process без отдельного sandbox/queue;
- diagnostics используют shared secret, а role-based admin появится после AUTH-001;
- Trudvsem worker остаётся внутри Gunicorn до SYNC-001;
- WAF, centralized error monitoring, backup alerts и incident runbook относятся к OPS-001.

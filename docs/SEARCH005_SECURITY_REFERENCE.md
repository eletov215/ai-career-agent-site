# AI Career Agent — security reference SEARCH-005

| Поле | Значение |
|---|---|
| Документ | SEARCH005_SECURITY_REFERENCE |
| Пакет | SEARCH-005 |
| Версия | 1.0 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Authorization boundary

```text
active server-side first-party session
+ verified User
+ exact normalized email in SEARCH_ADMIN_EMAILS
```

No diagnostics header, OAuth identity, provider token or obscured URL grants access. Ordinary user receives neutral 404.

## 2. Data minimization

The table has no user foreign key. Only operational aggregates are persisted. Admin page/API are read-only, rate-limited and `no-store`.

## 3. Threats and controls

| Threat | Control |
|---|---|
| ordinary user enumerates admin route | auth + allowlist + neutral 404 |
| credentials exposed as configuration state | boolean/reason only; env values never returned |
| provider body/error leaks | strict status/class sanitizer; no arbitrary message |
| user query leaks through telemetry | instrumentation extracts provider/outcome/latency only |
| zip/log/runtime artifact in release | repository hygiene and archive scan |
| stale state misrepresented | explicit stale flag/threshold and cached state |
| page triggers upstream abuse | no external probe on read |
| admin page cached by browser/proxy | no-store, no ETag |
| telemetry failure breaks search | non-gating try/fail-safe recording |
| multi-process gaps | documented residual risk; future shared transport |

## 4. Environment handling

`SEARCH_ADMIN_EMAILS` is deployment configuration. Repository examples remain empty. Changing it requires deploy/restart according to hosting environment. It is not logged.

## 5. Incident response

Empty/remove allowlist to disable route, preserve DB/log evidence, verify page/API payloads, rotate provider credentials only if independent evidence suggests exposure, and follow SEC/OPS incident procedure.

## 6. Rollback

Application revert or allowlist removal is preferred. Migration downgrade deletes only operational source health rows.

## 7. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 19.08.2026 | Admin authorization, minimization, telemetry sanitization, cache/log controls and incident boundary defined. |

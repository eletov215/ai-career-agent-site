# AI Career Agent — реализация PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_IMPLEMENTATION |
| Пакет | PRIV-001 |
| Версия | 1.2 |
| Дата | 19 августа 2026 |
| Статус | ВЫПОЛНЕНО |
| Рабочая основа | GitHub main после hardened v1.4.28 + CI hotfix r1 |
| Production revision | `20260813_0013` |

## 1. Контрольный статус

PRIV-001 реализован, прошёл full GitHub CI, Render migration/readiness `0013`, destructive production E2E, restart/regression и Render log privacy/error review. Пакет закрыт как **ВЫПОЛНЕНО**.

## 2. Цель и границы

Цель — дать first-party User технические средства получить читаемую копию поддерживаемых данных, удалить аккаунт и применить прозрачную retention baseline до публичного AI-контура.

В scope: re-authenticated owner export; current-password + exact-phrase deletion; local HH/SJ credential cleanup; cascade AUTH/PROFILE/RESUME cleanup; identifier-free audit; retention service/CLI/worker; orphan asset cleanup; UI/migration/backup/tests/CI.

Не входят: legal qualification/consent wording (`LEGAL-001`), remote provider-side OAuth grant revoke, external portability guarantee, background large-export queue, external object-storage deletion API, future AI/JOB/BILL data.

## 3. Export contract

`POST /privacy-center/export` требует active session, CSRF, current password и rate limit. PostgreSQL export использует consistent snapshot/owner lock. ZIP формируется через bounded spooled temporary storage и содержит:

```text
manifest.json
data.json
assets/<safe-owner-paths>   # только если owned referenced assets существуют
```

Export исключает password/session/token hashes, OAuth access/refresh/browser secrets и server secrets. Provider profile проходит sanitizer. Unsafe path components нормализуются; cross-owner/draft asset inconsistency fail-closed. Response `no-store`, без ETag.

## 4. Account deletion

`POST /privacy-center/delete-account` требует active User, CSRF, exact phrase `УДАЛИТЬ АККАУНТ` и current password. Password hash повторно сверяется внутри transaction после User row lock. Единый lock order координирует конкурентные password-reset/Auth/OAuth операции. После explicit legacy HH/SJ mirror cleanup удаляется User; FK cascade очищает AuthSession/AuthToken/OAuthConnection/CareerProfile/versions/ResumeDraft/versions/assets/exports. Browser session завершается.

## 5. Retention baseline

| Категория | Technical default | Действие |
|---|---:|---|
| Pending unverified User | 30 дней | stale cascade delete |
| Expired/revoked auth artifacts | 30 дней | bounded cleanup |
| Orphan ResumeAsset | 7 дней | delete only if no current/history reference after recheck |
| Identifier-free privacy audit | 180 дней | age-out |
| Cleanup cadence | 24 часа | periodic worker |
| Active owner data | until explicit deletion | automatic inactivity deletion отсутствует |

Это technical baseline, не legal claim. Final retention/privacy wording остаётся `LEGAL-001`; backup retention/restore policy — `OPS-002`/release gates.

## 6. Migration 20260813_0013

Migration создаёт `privacy_audit_events` и индекс `idx_resume_assets_created`. Existing AUTH/PROF/RESUME owner schemas не переписываются. Audit row не содержит User FK/email/provider identity/content.

## 7. Влияние на код и сайт

Ключевые области: `models/privacy.py`, `repositories/privacy.py`, `services/privacy.py`, `routes/privacy_controls.py`, privacy templates, `cleanup_privacy.py`, privacy worker, runtime/Compose/Render/VPS manifests, backup inventory, migration/tests/CI. В UI появляется «Мои данные» для export/delete; destructive form явно отделена.

## 8. Проверки и production evidence

- Hardened local suite: compile/migration/Alembic/Jinja/hygiene/infra/privacy tests green; final reported split suite `268 passed, 12 skipped, 0 failed` before GitHub runtime gates.
- First GitHub PRIV route gate выявил stale test expectation `401 == 200` после deleted-account relogin; CI hotfix r1 изменил только test contract.
- Повторный GitHub Actions полностью green, включая dedicated PRIV-001, PostgreSQL integration/migrations, AUTH/PROF regressions, backup/restore, Docker/runtime и full tests.
- Render `/health/ready`: current/expected `0013`, persistent PostgreSQL, migrations ok, privacy worker alive/status ok.
- Export: readable ZIP; no forbidden password/token fields; account without image references correctly has no `assets/`; account with university logo exports owned asset.
- Delete: wrong phrase/password safe; throwaway account exact delete succeeds; relogin/old URLs fail; second/main account unaffected.
- Restart/regression/log review passed.

## 9. Ограничения и риски

- Large exports remain synchronous web operations, though bounded/spooled.
- Current rate-limit backend is staging single-instance memory.
- Remote provider grant revoke is not claimed.
- Backup copies are not rewritten by account deletion.
- Final legal retention/consent wording pending.

## 10. Rollback

Application revert may keep additive `0013`. Controlled downgrade removes privacy audit/index changes but cannot resurrect an already deleted account. Recovery requires verified backup and explicit decision.

## 11. Следующее действие

`SEARCH-005` — ГОТОВО К СТАРТУ. Before code changes audit source-status, observability metrics, SyncRun/checkpoint telemetry and admin authorization boundary.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Initial export/delete/retention candidate. |
| 1.1 | 19.08.2026 | Hardened candidate: re-auth snapshot export, bounds/sanitizer/concurrency/orphan-asset controls. |
| 1.2 | 19.08.2026 | Green CI/Render `0013` and full production E2E/restart/log evidence; package COMPLETE. |


## AI-001 delta / 1.5.0 / 2026-09-14

AI export adds bounded owner-only usage metadata; no prompt/output contents. Account deletion removes owned AI ledger/plan/bucket rows; global aggregate costs and anonymous unexpired leases remain for safety. Existing privacy worker invokes bounded AI metadata cleanup after the original cleanup.

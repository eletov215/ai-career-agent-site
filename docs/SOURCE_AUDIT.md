# AI Career Agent — аудит источников v1.4.27

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.28 |
| Дата | 19 августа 2026 |
| Проверяемый пакет | PROF-003 closure + PRIV-001 candidate |
| Рабочий источник кода | GitHub `main` после PROF-003 hotfix r4; актуальный ZIP `ai-career-agent-site-main (17).zip`; PRIV-001 candidate построен поверх него |
| Production revision | `20260812_0012` |
| Candidate revision | `20260813_0013` |
| Результат | PROF-003 ВЫПОЛНЕНО; PRIV-001 НУЖНА ПРОВЕРКА |

## 1. Контрольный статус

Пользователь подтвердил последний обязательный PROF-003 gate: `/profile`, PROF-002 import/review/confirm, `/dashboard`, login/logout, HH/SuperJob state, `/vacancies`, ordinary search и `/health/ready=0012` работают штатно; Render log review не выявил новых 500/Traceback/migration errors или чувствительных resume/session payload. Поэтому PROF-003 переводится в **ВЫПОЛНЕНО**.

Следующий пакет по канонической очереди — PRIV-001. Candidate реализован поверх фактически подтверждённого PROF-003 baseline и остаётся **НУЖНА ПРОВЕРКА** до feature-branch PR, полного GitHub Actions, Render migration `0013` и production E2E.

## 2. Проверенная рабочая основа

- WSGI остаётся `app.py` / `app:app`; `app_fixed.py` отсутствует.
- Production PostgreSQL до PRIV-001 deploy остаётся `20260812_0012`.
- `infra/vps/.env.example` является обязательным secret-free template; реальный `.env` не включается.
- PROF-001/002/003 confirmed data, resume drafts/versions/assets/export metadata являются owner-scoped.
- PROF-003 final log boundary запрещает answers/messages/full snapshot/image bytes/cookies/session tokens.

## 3. PRIV-001 candidate implementation

| Область | Реализация |
|---|---|
| Data export | `POST /privacy-center/export` формирует ZIP с `manifest.json`, `data.json` и owned resume image assets |
| Secret exclusions | password hash, auth/session/token hashes, OAuth access/refresh credentials и browser state в export не включаются |
| Account deletion | exact phrase `УДАЛИТЬ АККАУНТ` + current password; после delete browser session очищается |
| Cascade | User/Auth/OAuth/Profile/Resume subtree удаляется FK cascade; legacy HH/SuperJob local credential mirrors удаляются явно |
| Audit | migration `20260813_0013` создаёт identifier-free `privacy_audit_events`: event type + bounded aggregate counts + timestamp |
| Retention | one-shot CLI + periodic worker очищают stale pending accounts, expired/revoked auth artifacts и старый identifier-free audit |
| Infrastructure | Render supervisor запускает privacy worker sibling; Compose имеет отдельный `privacy` profile; VPS env template содержит только non-secret knobs |
| UI | dashboard/navigation/footer -> «Мои данные»; privacy-center export/delete; public privacy page описывает фактические controls |

## 4. Technical retention baseline

```text
pending unverified account       30 days
expired/revoked auth artifacts   30 days
identifier-free privacy audit   180 days
cleanup interval                  24 hours
active profile/resume data        until explicit account deletion
```

Это техническая baseline policy, а не заявление о соответствии конкретному законодательству. `LEGAL-001` может изменить сроки и формулировки до публичного коммерческого релиза.

## 5. Security and privacy boundaries

- Export доступен только active first-party User и никогда не содержит authentication/OAuth secret material.
- Account deletion не выполняется только по session possession: требуется текущий password и точная confirmation phrase.
- Identifier-free audit специально не хранит user ID, email, filename, asset ID, resume content или provider identity.
- Logs PRIV-001 содержат только aggregate counts; delete password/export payload не логируются.
- Remote provider-side OAuth grant revocation не автоматизирован. Current contract удаляет локальные encrypted credentials и legacy mirrors; не заявлять provider-side revoke без отдельного API evidence.

## 6. Local evidence

- Python compileall — passed.
- Focused PRIV-001/config/infra/architecture/migration tests — passed (`86 passed, 1 expected local skip` в среде без Flask runtime).
- SQLite clean upgrade to `0013`, downgrade `0013 -> 0012`, re-upgrade `0012 -> 0013` — passed.
- `alembic check` — no new upgrade operations.
- Jinja parse — 28 templates passed.
- Repository hygiene / infra manifest / document structure — passed после удаления runtime caches.
- Full GitHub runtime tests ещё обязательны; локальный environment не содержит Flask dependencies для route E2E.

## 7. External gate

```text
branch priv-001-candidate-v1.4.27
-> Pull Request
-> full GitHub Actions GREEN, включая Verify PRIV-001 privacy export deletion and retention controls
-> merge main
-> Render deploy / migration 20260813_0013
-> /health/ready current=expected=0013
-> production E2E on throwaway account
-> restart + log review
-> PRIV-001 COMPLETE
```

## 8. Rollback

Application revert может оставить additive `0013`; previous code игнорирует privacy audit table. Controlled downgrade `0013 -> 0012` удаляет только identifier-free audit rows. Уже выполненное account deletion не отменяется downgrade и восстанавливается только из заранее verified backup по explicit decision.

## 9. Следующее действие

PRIV-001 candidate -> Pull Request CI. При любом красном gate merge запрещён. После полного production E2E следующий функциональный пакет — SEARCH-005.

## 10. Новые канонические версии

```text
PLAN_CURRENT 1.4.27
PROJECT_PASSPORT 2.41
SOURCE_AUDIT 1.4.27
PROF003 docs 1.2 COMPLETE
PRIV001_IMPLEMENTATION 1.0
PRIV001_VERIFICATION_STATUS 1.0
PRIV001_RUNBOOK 1.0
PRIV001_PRIVACY_REFERENCE 1.0
PRIV001_SECURITY_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.26 | 13.08.2026 | PROF-003 production evidence зафиксирован; final regression/log review pending. |
| 1.4.27 | 13.08.2026 | Final regression/log review подтверждён, PROF-003 закрыт. PRIV-001 candidate реализован с export/delete/retention/audit migration `0013`; external verification pending. |

## Hardened candidate v1.4.28

Повторный privacy/security аудит перед внешней проверкой усилил candidate: экспорт требует повторного текущего пароля и формируется как согласованный PostgreSQL snapshot; добавлены raw/archive size bounds, SpooledTemporaryFile, safe ZIP entry paths, OAuth profile sanitization и fail-closed owner/draft asset integrity. Account deletion повторно сверяет password hash под User row lock и использует единый lock order для Auth/OAuth rows. Retention cleanup получил bounded batches, orphan ResumeAsset cleanup (7d, только без current/history references), cross-process worker lock/heartbeat и индекс `idx_resume_assets_created`. Backup copies не переписываются account deletion; remote provider-side OAuth revoke не заявляется. Candidate schema остаётся `20260813_0013`; production до merge остаётся `20260812_0012`.

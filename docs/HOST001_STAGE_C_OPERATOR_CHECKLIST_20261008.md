# HOST-001 Stage C — operator checklist

| Field | Value |
|---|---|
| Date | 8 October 2026 |
| Baseline main | `6df77b65374ffbc3bf5df2612b074cd43b94504e` |
| Scope | One bounded synthetic Stage C field test |
| Owner ceiling | <= 1,000 RUB total / <= 4 hours |
| Automated hold | 90 minutes maximum |
| Production data | FORBIDDEN |
| Render / Neon changes | FORBIDDEN |
| MIG-001 | NOT AUTHORIZED |
| Real-data AI / Alice | 0 calls |
| Email / employer delivery | 0 sends |
| Default exit | Full teardown |

This checklist is the execution companion for `HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md`.
It does not authorize production migration or continuation of the foundation.

## 1. Stop conditions before starting the billed window

Do not dispatch `HOST-001 Stage C bounded apply` unless all of the following are true:

- current `main` is the reviewed commit and required CI/QA is accepted;
- `stage-c-yandex` contains the ten protected environment secrets;
- the dedicated Terraform-state bucket and its temporary S3 access key are active;
- the local private SSH key `~/.ssh/aca_stage_c_ed25519` is available to the operator;
- the exact plaintext values corresponding to `YC_STAGE_C_POSTGRES_PASSWORD` and `YC_STAGE_C_RESTORE_PASSWORD` are still available in the operator's password manager / local secure storage. Do not paste them into chat or GitHub comments;
- the operator can access Yandex Cloud Lockbox in the console;
- no production credentials, production SQL dump, OAuth token, user file or real email address will be used.

If either database password is no longer retrievable, stop before apply and rotate the matching GitHub Environment secret first. Do not try to discover a GitHub secret value from logs.

## 2. Dispatch

Run only:

- workflow: `HOST-001 Stage C bounded apply`;
- branch: `main`;
- acknowledgement: `APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H`;
- `hold_minutes=90`.

Run it once.

The workflow must pass the remote-state overlap guard and create-only allowlist plan, then dispatch the independent teardown workflow before Terraform apply.

If `Fresh reviewed Stage C plan` fails, stop. Do not rerun repeatedly. Use only the sanitized diagnostic printed by the workflow.

## 3. Record the live boundary immediately after apply

After `Apply reviewed Stage C plan` is green, open the job summary and record these non-secret values:

- apply run ID;
- exact commit SHA;
- public IPv4;
- primary PostgreSQL RW FQDN;
- runtime Lockbox secret ID;
- Stage C backup bucket name;
- backup Lockbox secret ID;
- restore PostgreSQL RW FQDN;
- remote Terraform state key.

The automatic 90-minute field window starts after successful apply. Treat T+70 minutes as the operational stop point for new test work and preserve the remainder for evidence and teardown observation.

## 4. Connect to the VM

From the operator workstation:

```bash
ssh -i ~/.ssh/aca_stage_c_ed25519 acaadmin@<PUBLIC_IP>
```

On the VM:

```bash
sudo -i
set -euo pipefail
cloud-init status --wait
test -s /etc/ai-career-agent/yandex-ca.pem
source /etc/ai-career-agent/host.env
test -n "$YC_LOCKBOX_SECRET_ID"
test -n "$YC_BACKUP_LOCKBOX_SECRET_ID"
test -n "$BACKUP_S3_BUCKET"
```

Prepare the exact reviewed repository revision:

```bash
cd /opt/ai-career-agent
if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git
fi
if [ ! -d .git ]; then
  git clone https://github.com/eletov215/ai-career-agent-site.git .
fi
git fetch --all --prune
git checkout --detach <APPLY_COMMIT_SHA>
test "$(git rev-parse HEAD)" = "<APPLY_COMMIT_SHA>"
```

Do not checkout a newer commit during the live field test.

## 5. Populate the runtime Lockbox secret

Use Yandex Cloud console -> Lockbox -> the `runtime Lockbox secret ID` from the apply summary -> add a new payload version.

Do not use production provider credentials. The Stage C payload may contain only synthetic / field-test values.

Required entries:

```text
DATABASE_URL
RESTORE_DATABASE_URL
FLASK_SECRET_KEY
TOKEN_ENCRYPTION_KEY
SUPERJOB_CLIENT_ID
SUPERJOB_CLIENT_SECRET
SUPERJOB_REDIRECT_URI
HH_CLIENT_ID
HH_CLIENT_SECRET
HH_REDIRECT_URI
HH_USER_AGENT
SYNC_SECRET
TRUSTED_HOSTS
BACKUP_ENCRYPTION_KEY
AUTH_EMAIL_BACKEND
PRIVACY_CLEANUP_ENABLED
```

Use:

```text
AUTH_EMAIL_BACKEND=disabled
PRIVACY_CLEANUP_ENABLED=0
SUPERJOB_CLIENT_ID=stage-c-disabled
SUPERJOB_CLIENT_SECRET=stage-c-disabled
HH_CLIENT_ID=stage-c-disabled
HH_CLIENT_SECRET=stage-c-disabled
HH_USER_AGENT=AI-Career-Agent-Stage-C/1.0 (stage-c@example.invalid)
SUPERJOB_REDIRECT_URI=https://stage-c.invalid/oauth/superjob/callback
HH_REDIRECT_URI=https://stage-c.invalid/oauth/hh/callback
TRUSTED_HOSTS=<PUBLIC_IP>,stage-c.invalid
```

Generate independent synthetic secrets locally; do not put their output into chat:

```bash
openssl rand -hex 32
openssl rand -base64 32 | tr '+/' '-_'
openssl rand -base64 32 | tr '+/' '-_'
openssl rand -hex 32
```

Use those outputs respectively for `FLASK_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_KEY` and `SYNC_SECRET`.

Construct the primary URL using the exact password stored for `YC_STAGE_C_POSTGRES_PASSWORD`:

```text
postgresql+psycopg://ai_career_agent:<URL_ENCODED_PASSWORD>@<PRIMARY_PG_FQDN>:6432/ai_career_agent?sslmode=verify-full&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem&target_session_attrs=read-write
```

Construct the isolated restore URL using `YC_STAGE_C_RESTORE_PASSWORD`:

```text
postgresql+psycopg://aca_restore:<URL_ENCODED_PASSWORD>@<RESTORE_PG_FQDN>:6432/aca_restore?sslmode=verify-full&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem&target_session_attrs=read-write
```

A password containing `+`, `/`, `=`, `@`, `:`, `?`, `#` or other reserved URL characters must be percent-encoded before it is placed in either URL.

## 6. Verify Lockbox loading and PostgreSQL TLS before migration

On the VM:

```bash
cd /opt/ai-career-agent
source /etc/ai-career-agent/host.env

python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm ops sh -lc '
    libpq_url="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
    psql "$libpq_url" -Atc "SHOW server_version;"
  '
```

PASS requires PostgreSQL major version 18.

Verify the target is writable:

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm ops sh -lc '
    libpq_url="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
    psql "$libpq_url" -Atc "SELECT pg_is_in_recovery();"
  '
```

PASS requires `f`.

Wrong-CA drill must fail closed. Do not print the database URL:

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm ops sh -lc '
    bad_url="$(python - <<'"'"'PY'"'"'
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
u = urlsplit(os.environ["DATABASE_URL"])
q = dict(parse_qsl(u.query, keep_blank_values=True))
q["sslrootcert"] = "/tmp/stage-c-bad-ca.pem"
print(urlunsplit(("postgresql", u.netloc, u.path, urlencode(q), u.fragment)))
PY
)"
    printf "not-a-ca\n" >/tmp/stage-c-bad-ca.pem
    if psql "$bad_url" -Atc "SELECT 1" >/dev/null 2>&1; then
      echo "FAIL: wrong CA was accepted"
      exit 1
    fi
    echo "PASS: wrong CA rejected"
  '
```

## 7. Explicit migration and schema check

Run only the one-off migration service:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml run --rm --build migrate
```

Then verify:

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm ops sh -lc '
    libpq_url="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
    psql "$libpq_url" -Atc "SELECT version_num FROM alembic_version;"
  '
```

PASS requires:

```text
20261002_0023
```

Do not start `sync-worker` or `privacy-worker` during Stage C.

Before creating the backup, seed the deterministic synthetic fixture. The helper refuses to seed a database that already contains unrelated users and keeps legal consent withdrawn/provider=`none`.

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm ops python scripts/host001_stage_c_fixture.py seed \
    --acknowledgement SEED_STAGE_C_SYNTHETIC_ONLY \
    --report /var/backups/ai-career-agent/stage-c-source-report.json
```

PASS requires `ok=true`. Preserve the secret-free source report in the backup volume; it contains the deterministic fixture digest, resume-asset SHA-256, representative schema-object digest and PostgreSQL sequence state used by the restore verification.

## 8. Start only web + gateway

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml up -d --build web gateway

docker compose -f infra/yandex-cloud/compose.yaml ps
```

From the operator workstation:

```bash
curl -fsS --max-time 10 "http://<PUBLIC_IP>/health/live"
curl -fsS --max-time 10 "http://<PUBLIC_IP>/health/ready"
```

Do not test OAuth provider login, real email delivery or AI provider calls.

## 9. Create and verify the encrypted synthetic backup

On the VM:

```bash
cd /opt/ai-career-agent
source /etc/ai-career-agent/host.env

python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm ops python scripts/backup_database.py     --output-dir /var/backups/ai-career-agent     --name stage-c-synthetic.dump
```

The output must report `ok=true`, `encrypted=true`, schema revision `20261002_0023`, and a SHA-256.

Verify locally in the ops volume:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm ops python scripts/verify_backup.py     --backup /var/backups/ai-career-agent/stage-c-synthetic.dump.enc
```

## 10. Export backup off the VM

The second Lockbox secret created by Terraform already contains the temporary Stage C Object Storage access credentials.

Run the nested Lockbox export path:

```bash
python infra/yandex-cloud/run_with_lockbox.py --secret-id "$YC_LOCKBOX_SECRET_ID" --   python infra/yandex-cloud/run_with_lockbox.py --secret-id "$YC_BACKUP_LOCKBOX_SECRET_ID" --   docker compose -f infra/yandex-cloud/compose.yaml --profile backup-export     run --rm     -e BACKUP_EXPORT_FILE=stage-c-synthetic.dump.enc     -e BACKUP_EXPORT_MANIFEST=stage-c-synthetic.dump.enc.manifest.json     backup-export
```

PASS requires JSON with `"ok": true`. Do not print presigned URLs or Object Storage keys.

Verify the two objects exist from the Yandex Object Storage console. Do not open or share the object contents.

## 11. Restore into the isolated PostgreSQL 18 target

Run restore against `RESTORE_DATABASE_URL` from the runtime Lockbox payload:

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm \
    -e RESTORE_DATABASE_URL \
    -e APP_ENV=development \
    ops python scripts/restore_database.py \
      --backup /var/backups/ai-career-agent/stage-c-synthetic.dump.enc \
      --manifest /var/backups/ai-career-agent/stage-c-synthetic.dump.enc.manifest.json
```

The `APP_ENV=development` override applies only to the one-off restore helper so its production-restore interlock recognizes the target as disposable. It does not change the web/gateway runtime, which remains `APP_ENV=production`.

PASS requires:

- `ok=true`;
- `verified=true`;
- revision `20261002_0023`;
- source and restored inventory counts equal.

Then verify representative owner/JOB/legal rows, exact resume-asset bytes, named indexes/constraints and PostgreSQL sequence state against the pre-backup source report:

```bash
python infra/yandex-cloud/run_with_lockbox.py -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile ops \
  run --rm \
    -e RESTORE_DATABASE_URL \
    ops python scripts/host001_stage_c_fixture.py verify \
      --database-env RESTORE_DATABASE_URL \
      --expected-report /var/backups/ai-career-agent/stage-c-source-report.json
```

PASS requires `ok=true` and no restore-verification mismatch.

The restore database is disposable and synthetic-only. Never point `RESTORE_DATABASE_URL` at Render, Neon or any production database.

## 12. Proxy / client-IP smoke

Use the existing app-facing rate-limit probe exactly once. Vary both forged headers on every request:

```bash
for i in 1 2 3 4 5 6; do
  code="$(curl -o /dev/null -sS --max-time 10 -w '%{http_code}' \
    -H "CF-Connecting-IP: 203.0.113.$i" \
    -H "X-Forwarded-For: 198.51.100.$i" \
    "http://<PUBLIC_IP>/api/security/rate-limit-probe")"
  printf 'attempt=%s status=%s\n' "$i" "$code"
done
```

PASS requires statuses `200,200,200,200,200,429`. Because every forged `CF-Connecting-IP` and `X-Forwarded-For` value differs, reaching the single five-request limiter bucket is app-facing evidence that Caddy removed the client-supplied Cloudflare identity and rebuilt `X-Forwarded-For` from the stable network peer. Six `200` responses are a FAIL.

Do not repeat the probe during the same minute, enable debug diagnostics or weaken proxy/security settings.

## 13. Trudvsem observation — non-blocking

At most three requests, no response body retention:

```bash
for i in 1 2 3; do
  curl -o /dev/null -sS     --connect-timeout 5     --max-time 15     -w "attempt=$i status=%{http_code} total=%{time_total}\n"     "https://opendata.trudvsem.ru/api/v1/vacancies"
done
```

Record only status, latency and error type. Trudvsem success is not a Stage C acceptance gate.

## 14. T+70 stop point

At T+70 after successful apply:

- do not begin any new test;
- record PASS/FAIL/NOT_RUN for PostgreSQL/TLS, migration, health, backup, export, restore, proxy and Trudvsem;
- stop web/gateway if practical:

```bash
docker compose -f infra/yandex-cloud/compose.yaml down
```

Do not cancel the already-dispatched automatic teardown workflow.

## 15. Automatic teardown

The default outcome is full destruction.

The separate `HOST-001 Stage C recovery teardown` workflow must:

- open the exact state `host001/stage-c-<SOURCE_RUN_ID>.tfstate`;
- review a delete/read/no-op-only plan;
- delete the VM/public IP, both PostgreSQL clusters, temporary static key, Lockbox secrets, backup bucket and other Terraform-managed Stage C resources;
- verify Terraform owns zero managed resources.

If automatic teardown fails or is cancelled, immediately run the recovery workflow manually from `main` with:

```text
acknowledgement=DESTROY_STAGE_C_SYNTHETIC_1000_RUB
source_sha=<APPLY_COMMIT_SHA>
source_run_id=<APPLY_RUN_ID>
hold_minutes=0
```

Do not start another apply while any previous Stage C state owns resources.

## 16. Final cleanup after verified Terraform teardown

Only after Terraform reports zero managed resources and Yandex console confirms that Stage C billable resources are gone:

1. preserve the issue/run evidence and actual billed amount;
2. revoke the temporary Terraform-state static access key;
3. delete the dedicated Terraform-state bucket only after the state/evidence is no longer needed for recovery;
4. revoke/reduce temporary folder write roles from `aca-stage-c-terraform-plan` (`editor` and `resource-manager.admin`);
5. confirm no VM, public IPv4, Managed PostgreSQL cluster, Stage C backup bucket, temporary static access key or Stage C Lockbox secret remains;
6. keep Render/Neon unchanged.

Stage C can be marked PASS only after both the synthetic acceptance evidence and verified teardown are complete.

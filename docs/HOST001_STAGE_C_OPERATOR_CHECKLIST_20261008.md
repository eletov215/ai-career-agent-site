# HOST-001 Stage C operator checklist — 2026-10-08

Status: **PRE-APPLY OPERATOR PACKAGE / SYNTHETIC ONLY**

This checklist is the execution companion for `HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md`.
It is intentionally narrow and does not authorize production migration, Render/Neon changes,
real-data AI/provider calls, email delivery, legal activation, payment activation, or MIG-001.

The owner-authorized boundary is:

- synthetic data only;
- total Stage C ceiling: **<=1,000 RUB**;
- absolute lifetime ceiling: **<=4 hours**;
- bounded apply successful-field window: **15-90 minutes**;
- default outcome: automatic full teardown;
- no production/user data.

Do not start the bounded apply until every item in section 1 is true.

## 1. Zero-spend readiness before bounded apply

### 1.1 GitHub / cloud controls

Confirm:

- `main` is green;
- `stage-c-yandex` still contains the 10 protected environment secrets;
- the environment still allows only `main`;
- the dedicated remote-state bucket exists and remains private;
- the temporary Stage C Terraform service account still has only the reviewed folder-scoped write roles required by the Stage C apply/teardown path;
- no previous Stage C state object owns managed resources;
- no other Stage C apply/recovery run is active.

Do not create or broaden any cloud-wide administrator role.

### 1.2 SSH reachability

The Stage C VM allows SSH only from `YC_STAGE_C_ADMIN_CIDR`.

Before starting paid time:

- use the same network/VPN state that was used when `YC_STAGE_C_ADMIN_CIDR` was recorded;
- confirm the dedicated private key is available locally:

```bash
test -f ~/.ssh/aca_stage_c_ed25519
chmod 600 ~/.ssh/aca_stage_c_ed25519
```

If the external IPv4 has changed, update only `YC_STAGE_C_ADMIN_CIDR`, rerun the no-apply credentialed plan, and do not start bounded apply until that plan is green.

### 1.3 Database passwords must be recoverable by the operator

GitHub does not reveal environment secret values after saving them.

Before bounded apply, the operator must have the plaintext values of both:

- `YC_STAGE_C_POSTGRES_PASSWORD`;
- `YC_STAGE_C_RESTORE_PASSWORD`.

Never paste either value into chat, an issue, Actions logs, or a commit.

If either value was not retained, rotate both GitHub environment secrets before apply. Prefer URL-safe values so the PostgreSQL URLs do not require manual percent-encoding, for example:

```bash
openssl rand -hex 24
```

Store the two new values in the operator password manager, update the two GitHub environment secrets, and rerun only the no-apply Stage C plan.

### 1.4 Pre-generate synthetic runtime secret values

Prepare these values in a password manager before paid time starts:

```bash
# FLASK_SECRET_KEY
python3 -c 'import secrets; print(secrets.token_hex(32))'

# TOKEN_ENCRYPTION_KEY (valid Fernet key format)
python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'

# BACKUP_ENCRYPTION_KEY (32-byte URL-safe base64)
python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'

# SYNC_SECRET
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Do not store these in Git, shell history, issue comments, or chat.

The remaining required OAuth values are synthetic placeholders only; they are present solely because production configuration validation requires non-empty values:

```text
SUPERJOB_CLIENT_ID=host001-stage-c-disabled
SUPERJOB_CLIENT_SECRET=host001-stage-c-disabled
SUPERJOB_REDIRECT_URI=https://stage-c.invalid/oauth/superjob/callback
HH_CLIENT_ID=host001-stage-c-disabled
HH_CLIENT_SECRET=host001-stage-c-disabled
HH_REDIRECT_URI=https://stage-c.invalid/oauth/hh/callback
HH_USER_AGENT=AI-Career-Agent-Stage-C/1.0 (synthetic@example.invalid)
```

Do not use real provider credentials in Stage C.

## 2. Start the bounded apply

Run exactly one GitHub Actions workflow:

```text
HOST-001 Stage C bounded apply
branch: main
acknowledgement: APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H
hold_minutes: 90
```

If `Fresh reviewed Stage C plan` fails, stop. Do not rerun blindly. Use only the sanitized diagnostic emitted by the workflow.

If the plan succeeds, the workflow must dispatch the independent teardown before `terraform apply`.

After `Apply reviewed Stage C plan` succeeds, immediately record from the Actions summary:

- exact commit SHA;
- apply run ID;
- public IPv4;
- primary PostgreSQL RW FQDN;
- runtime Lockbox secret ID;
- field-test backup bucket;
- backup Lockbox secret ID;
- disposable restore PostgreSQL RW FQDN.

These are operational coordinates, not secret payload values.

## 3. Populate the runtime Lockbox secret

In Yandex Cloud Console open the runtime Lockbox secret ID shown by the successful apply summary and add one payload version.

Use only synthetic values.

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
```

Set:

```text
AUTH_EMAIL_BACKEND=disabled
TRUSTED_HOSTS=<PUBLIC_IP_FROM_APPLY_SUMMARY>,127.0.0.1,localhost
```

Build the primary URL using the operator-held `YC_STAGE_C_POSTGRES_PASSWORD`:

```text
postgresql+psycopg://ai_career_agent:<PRIMARY_PASSWORD>@<PRIMARY_PG_RW_FQDN>:6432/ai_career_agent?sslmode=verify-full&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem&target_session_attrs=read-write
```

Build the restore URL using `YC_STAGE_C_RESTORE_PASSWORD`:

```text
postgresql+psycopg://aca_restore:<RESTORE_PASSWORD>@<RESTORE_PG_RW_FQDN>:6432/aca_restore?sslmode=verify-full&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem&target_session_attrs=read-write
```

The URL-safe password requirement in section 1.3 avoids URI encoding ambiguity.

Do not add Gmail, SMTP, Alice/Yandex AI, HH, SuperJob, Reed, or any other real provider credentials.

## 4. SSH and pin the exact repository commit

From the operator workstation:

```bash
ssh -i ~/.ssh/aca_stage_c_ed25519 acaadmin@<PUBLIC_IP>
```

On the VM:

```bash
cloud-init status --wait
docker --version
docker compose version
git --version

export YC_LOCKBOX_SECRET_ID="$(sudo sed -n 's/^YC_LOCKBOX_SECRET_ID=//p' /etc/ai-career-agent/host.env)"
export YC_BACKUP_LOCKBOX_SECRET_ID="$(sudo sed -n 's/^YC_BACKUP_LOCKBOX_SECRET_ID=//p' /etc/ai-career-agent/host.env)"
export BACKUP_S3_BUCKET="$(sudo sed -n 's/^BACKUP_S3_BUCKET=//p' /etc/ai-career-agent/host.env)"
export STAGE_C_EXPECTED_PRIMARY_PG_FQDN="$(sudo sed -n 's/^PRIMARY_PG_RW_FQDN=//p' /etc/ai-career-agent/host.env)"
export STAGE_C_EXPECTED_RESTORE_PG_FQDN="$(sudo sed -n 's/^RESTORE_PG_RW_FQDN=//p' /etc/ai-career-agent/host.env)"
test -n "$STAGE_C_EXPECTED_PRIMARY_PG_FQDN"
test -n "$STAGE_C_EXPECTED_RESTORE_PG_FQDN"

Every subsequent `run_with_lockbox.py` invocation now compares `DATABASE_URL` to `STAGE_C_EXPECTED_PRIMARY_PG_FQDN` and the reviewed `ai_career_agent` user/database before executing its command. This protects migration, web startup, health, backup and other primary-database commands from an accidentally pasted production URL.

cd /opt/ai-career-agent
git clone https://github.com/eletov215/ai-career-agent-site.git .
git checkout --detach <EXACT_COMMIT_FROM_APPLY_SUMMARY>
test "$(git rev-parse HEAD)" = "<EXACT_COMMIT_FROM_APPLY_SUMMARY>"
```

The VM image installs `git` through cloud-init specifically so this checkout can be completed without spending field-test time installing deployment tooling manually.

## 5. Validate Lockbox loading without printing secrets

On the VM, from `/opt/ai-career-agent`:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   python -c 'import json,os; required=("DATABASE_URL","RESTORE_DATABASE_URL","FLASK_SECRET_KEY","TOKEN_ENCRYPTION_KEY","SUPERJOB_CLIENT_ID","SUPERJOB_CLIENT_SECRET","SUPERJOB_REDIRECT_URI","HH_CLIENT_ID","HH_CLIENT_SECRET","HH_REDIRECT_URI","HH_USER_AGENT","SYNC_SECRET","TRUSTED_HOSTS","BACKUP_ENCRYPTION_KEY","AUTH_EMAIL_BACKEND"); missing=[k for k in required if not os.environ.get(k)]; print(json.dumps({"runtime_secret_loaded": not missing, "missing": missing}))'
```

Expected result:

```text
{"runtime_secret_loaded": true, "missing": []}
```

No secret values may be printed.

## 6. PostgreSQL 18 / TLS / writable-host checks

Build the PostgreSQL 18 ops image and verify the secure connection:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm --build ops   sh -lc 'psql "$DATABASE_URL" -Atc "SHOW server_version_num; SELECT pg_is_in_recovery();"'
```

Acceptance:

- `server_version_num` begins with `18`;
- `pg_is_in_recovery()` is `f`;
- the connection succeeds with `sslmode=verify-full`;
- the URL already contains `target_session_attrs=read-write`.

Wrong/untrusted-CA must fail closed:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm ops   python -c 'import os,urllib.parse,psycopg; u=urllib.parse.urlsplit(os.environ["DATABASE_URL"]); q=[(k,"/dev/null" if k=="sslrootcert" else v) for k,v in urllib.parse.parse_qsl(u.query,keep_blank_values=True)]; bad=urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,urllib.parse.urlencode(q),u.fragment)); ok=False
try:
 psycopg.connect(bad,connect_timeout=5)
except Exception:
 ok=True
print({"wrong_ca_blocked":ok})
raise SystemExit(0 if ok else 2)'
```

Expected:

```text
{"wrong_ca_blocked": True}
```

## 7. Explicit one-off migration

Do not start the broad migration profile.

Run only:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml   --profile migration run --rm --build migrate
```

Then verify the current revision:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml   --profile migration run --rm migrate   python scripts/manage_db.py current
```

Expected:

```text
20261002_0023
```

## 8. Seed the deterministic synthetic restore fixture

The repository contains `scripts/host001_stage_c_fixture.py`.

It is gated by the exact acknowledgement `HOST001_STAGE_C_SYNTHETIC_ONLY`, requires the database URL host to equal the exact Terraform-derived FQDN stored by cloud-init, uses only `.invalid` / synthetic rows, and does not call providers.

Seed the primary database and write secret-free baseline evidence into the backup volume:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm --build -e STAGE_C_EXPECTED_PRIMARY_PG_FQDN ops   python scripts/host001_stage_c_fixture.py seed   --ack HOST001_STAGE_C_SYNTHETIC_ONLY   --evidence /var/backups/ai-career-agent/host001-stage-c-fixture.json
```

The fixture covers:

- one synthetic owner;
- JOB saved vacancy + source ownership;
- withdrawn LEGAL-001 AI consent;
- resume draft/version/export metadata;
- resume asset bytes with a deterministic SHA-256;
- schema index/constraint signature;
- PostgreSQL public sequence inventory.

No accepted AI consent is left active.

## 9. Start only web + gateway

Do not start writer profiles.

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml   up -d --build web gateway
```

Check locally on the VM:

```bash
curl --fail --silent --show-error http://127.0.0.1/health/live
curl --fail --silent --show-error http://127.0.0.1/health/ready
docker compose -f infra/yandex-cloud/compose.yaml ps
```

Check from the operator workstation:

```bash
curl --fail --silent --show-error http://<PUBLIC_IP>/health/live
curl --fail --silent --show-error http://<PUBLIC_IP>/health/ready
```

The readiness payload must show the expected database revision and a healthy persistent database.

Because DOMAIN-001 is not part of Stage C, this smoke path intentionally uses HTTP only. Do not treat it as commercial TLS/domain acceptance.

## 10. Proxy/client-IP hardening probe

From the operator workstation, send six requests while changing forged forwarding headers:

```bash
for i in 1 2 3 4 5 6; do
  curl --silent --output /dev/null --write-out "%{http_code}\n"     -H "CF-Connecting-IP: 203.0.113.$i"     -H "X-Forwarded-For: 198.51.100.$i"     "http://<PUBLIC_IP>/api/security/rate-limit-probe"
done
```

Expected:

- the forged `CF-Connecting-IP` is removed by Caddy;
- `X-Forwarded-For` is rebuilt from the actual TCP peer;
- changing forged values does not evade the per-client rate limit;
- the controlled probe reaches HTTP `429` after its five-per-minute allowance.

## 11. Create, validate and export the encrypted backup

Create the backup:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm ops   python scripts/backup_database.py   --output-dir /var/backups/ai-career-agent   --name host001-stage-c
```

Expected files inside the `backup-data` volume:

```text
host001-stage-c.dump.enc
host001-stage-c.dump.enc.manifest.json
host001-stage-c-fixture.json
```

Validate the manifest/checksum:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm ops   python scripts/verify_backup.py   --backup /var/backups/ai-career-agent/host001-stage-c.dump.enc   --manifest /var/backups/ai-career-agent/host001-stage-c.dump.enc.manifest.json
```

Export the encrypted backup and manifest to the private Stage C Object Storage bucket:

```bash
export BACKUP_EXPORT_FILE=host001-stage-c.dump.enc
export BACKUP_EXPORT_MANIFEST=host001-stage-c.dump.enc.manifest.json

python infra/yandex-cloud/run_with_lockbox.py   --secret-id "$YC_LOCKBOX_SECRET_ID" --   python infra/yandex-cloud/run_with_lockbox.py   --secret-id "$YC_BACKUP_LOCKBOX_SECRET_ID" --   docker compose -f infra/yandex-cloud/compose.yaml   --profile backup-export run --rm --build backup-export
```

Expected final JSON:

```text
{"ok": true, ...}
```

The exporter authenticates the AES-256-GCM envelope before upload and never prints the generated presigned URLs or static secret key.

In Yandex Cloud Console, confirm only that the private backup bucket contains the two `field-test/` objects. Do not expose the bucket publicly.

## 12. Restore into the disposable PostgreSQL 18 target

Restore the encrypted local Stage C artifact into the dedicated `aca_restore` database:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm -e RESTORE_DATABASE_URL -e STAGE_C_EXPECTED_RESTORE_PG_FQDN ops   sh -lc 'python scripts/host001_stage_c_fixture.py guard-restore --ack HOST001_STAGE_C_SYNTHETIC_ONLY && python scripts/restore_database.py --backup /var/backups/ai-career-agent/host001-stage-c.dump.enc --manifest /var/backups/ai-career-agent/host001-stage-c.dump.enc.manifest.json --clean --allow-production'
```

`--allow-production` here is reached only after `guard-restore` proves that `RESTORE_DATABASE_URL` matches the exact Terraform-derived disposable Stage C restore FQDN plus the reviewed `aca_restore` user/database. Never reuse this command against a persistent or production database.

Then verify the representative synthetic fixture, byte-for-byte asset preservation, schema signature and sequence signature:

```bash
python infra/yandex-cloud/run_with_lockbox.py --   docker compose -f infra/yandex-cloud/compose.yaml --profile ops   run --rm -e RESTORE_DATABASE_URL -e STAGE_C_EXPECTED_RESTORE_PG_FQDN ops   python scripts/host001_stage_c_fixture.py verify   --ack HOST001_STAGE_C_SYNTHETIC_ONLY   --evidence /var/backups/ai-career-agent/host001-stage-c-fixture.json
```

Acceptance includes:

- revision = `20261002_0023`;
- backup/restore row counts match;
- synthetic JOB and withdrawn LEGAL structures match;
- synthetic resume asset bytes and SHA-256 match;
- selected indexes/constraints match;
- public PostgreSQL sequence inventory matches.

## 13. Optional Trudvsem Russia-location observation

This is diagnostic only and must not block Stage C.

From the Stage C VM, make at most three public requests, recording only status/latency:

```bash
for i in 1 2 3; do
  curl --silent --show-error --output /dev/null     --connect-timeout 5 --max-time 15     --write-out "attempt=$i status=%{http_code} total=%{time_total}\n"     "https://opendata.trudvsem.ru/api/v1/vacancies?limit=1&offset=1"
done
```

Do not store or inspect response payloads and do not start `sync-worker`.

## 14. Evidence that must be captured

Record only secret-free evidence:

- apply run ID and exact commit;
- successful create-only plan gate;
- public IP and non-secret resource coordinates from the Action summary;
- PostgreSQL 18 result;
- correct-CA success and wrong-CA rejection;
- migration revision;
- fixture seed JSON result;
- `/health/live` and `/health/ready` status;
- proxy/rate-limit HTTP status sequence;
- encrypted backup JSON result;
- Object Storage object-existence observation;
- restore JSON result;
- fixture verification JSON result;
- optional Trudvsem status/latency only;
- teardown run ID and final managed-resource count = 0.

Do not capture:

- passwords;
- private SSH keys;
- service-account JSON;
- S3 access/secret keys;
- Lockbox payload values;
- presigned URLs;
- DATABASE_URL / RESTORE_DATABASE_URL.

## 15. Stop conditions

Stop testing and allow immediate teardown if any of these occurs:

- owner-approved spend or <=4h ceiling can no longer be guaranteed;
- apply creates a resource outside the reviewed allowlist;
- independent teardown was not dispatched before apply;
- production/user data is introduced;
- a real provider/email/AI credential is accidentally loaded;
- database target identity is ambiguous;
- backup encryption/authentication fails;
- restore points to anything other than the disposable `aca_restore` target;
- Terraform remote state becomes unavailable;
- unexpected destructive/replacement action appears.

Do not extend the test window to debug a non-essential feature.

## 16. Teardown

Default outcome is **full teardown**.

The automatic recovery workflow owns the apply run's exact remote state and should delete:

- app VM;
- public IPv4;
- primary PostgreSQL cluster/user/database;
- disposable restore PostgreSQL cluster/user/database;
- runtime Lockbox secret;
- temporary backup Lockbox secret/static key;
- Stage C backup bucket;
- reviewed VPC/subnets/security groups/IAM bindings.

After automatic teardown:

1. verify the teardown workflow succeeded;
2. verify Terraform reports no managed resources in the apply run state;
3. verify no reviewed Stage C billable resources remain in Yandex Cloud;
4. only after evidence capture, revoke the temporary remote-state static access key;
5. delete the dedicated remote-state bucket;
6. revoke/reduce the temporary `editor` and `resource-manager.admin` roles from `aca-stage-c-terraform-plan`.

If automatic teardown fails, run only:

```text
HOST-001 Stage C recovery teardown
acknowledgement: DESTROY_STAGE_C_SYNTHETIC_1000_RUB
source_sha: <exact apply commit>
source_run_id: <exact apply run id>
hold_minutes: 0
```

Do not start another Stage C apply while any prior Stage C state still owns managed resources.

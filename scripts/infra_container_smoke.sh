#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

ENV_FILE=${ENV_FILE:-infra/vps/compose.test.env}
BASE_URL=${BASE_URL:-http://127.0.0.1:18000}
REPORT_DIR=${REPORT_DIR:-infra/reports}

mkdir -p "$REPORT_DIR"

cleanup() {
    docker compose --env-file "$ENV_FILE" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup
docker compose --env-file "$ENV_FILE" config >/dev/null
docker compose --env-file "$ENV_FILE" build web
docker compose --env-file "$ENV_FILE" up -d db
docker compose --env-file "$ENV_FILE" run --rm migrate
docker compose --env-file "$ENV_FILE" up -d web

for attempt in $(seq 1 60); do
    if curl --fail --silent --show-error "$BASE_URL/health/ready" >/dev/null; then
        break
    fi
    if [ "$attempt" -eq 60 ]; then
        docker compose --env-file "$ENV_FILE" logs web db
        exit 1
    fi
    sleep 2
done

container_id=$(docker compose --env-file "$ENV_FILE" ps -q web)
test -n "$container_id"
test "$(docker exec "$container_id" id -u)" != "0"

python scripts/infra_probe.py \
    --base-url "$BASE_URL" \
    --skip-outbound \
    --json-output "$REPORT_DIR/container-smoke.json" \
    --markdown-output "$REPORT_DIR/container-smoke.md" \
    --strict

printf 'INFRA-001 container smoke passed.\n'

#!/usr/bin/env bash
# One entry point for CDI Health Docker.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/docker/.env"
COMPOSE_FILE="$ROOT_DIR/deploy/docker/docker-compose.yml"
TEMPLATE="$ROOT_DIR/deploy/docker/nginx.remote-bench.conf.template"
GENERATED="$ROOT_DIR/deploy/docker/.nginx.remote-bench.generated.conf"

CDI_VERSION="${CDI_VERSION:-latest}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
BENCH_IP="${BENCH_IP:-}"
BUILD=0
PROFILE=local

usage() {
  cat <<USAGE
Usage: ./scripts/docker-up.sh [up|down|reset] [options]

Run the CDI Health dashboard + API from GHCR (:latest by default).

Commands:
  up       (default) ensure .env, pull/start stack
  down     stop containers
  reset    stop and remove API data volume

Options:
  --build          Build images from this repo instead of pulling GHCR
  --bench <ip>     Proxy the UI to a remote grading bench (no local API)
  -h, --help       Show this help

Environment:
  CDI_VERSION      GHCR tag (default: latest)
  DASHBOARD_PORT   Host UI port (default: 3000)
  BENCH_IP         Same as --bench <ip>

Examples:
  ./scripts/docker-up.sh
  ./scripts/docker-up.sh --build
  ./scripts/docker-up.sh --bench 192.168.0.74
  DASHBOARD_PORT=3001 ./scripts/docker-up.sh
  ./scripts/docker-up.sh down

Open http://127.0.0.1:\${DASHBOARD_PORT:-3000}
Enable **Use mock data** on Discover for fixture demos.
USAGE
}

ensure_env() {
  if [[ -f "$ENV_FILE" ]] && grep -qE '^CDI_HEALTH_API_TOKEN=.+' "$ENV_FILE" &&
    ! grep -qE '^CDI_HEALTH_API_TOKEN=replace-with-strong-token[[:space:]]*$' "$ENV_FILE"; then
    return 0
  fi
  mkdir -p "$(dirname "$ENV_FILE")"
  local token
  token="$(openssl rand -hex 24 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(24))')"
  if [[ -f "$ENV_FILE" ]]; then
    if grep -qE '^CDI_HEALTH_API_TOKEN=' "$ENV_FILE"; then
      local tmp
      tmp="$(mktemp)"
      sed "s|^CDI_HEALTH_API_TOKEN=.*|CDI_HEALTH_API_TOKEN=${token}|" "$ENV_FILE" >"$tmp"
      mv "$tmp" "$ENV_FILE"
    else
      printf '\nCDI_HEALTH_API_TOKEN=%s\n' "$token" >>"$ENV_FILE"
    fi
  else
    cat >"$ENV_FILE" <<EOF
DASHBOARD_PORT=${DASHBOARD_PORT}
CDI_HEALTH_API_TOKEN=${token}
EOF
  fi
  echo "Wrote ${ENV_FILE} (generated CDI_HEALTH_API_TOKEN)."
}

compose() {
  # shellcheck disable=SC2086
  env CDI_VERSION="$CDI_VERSION" DASHBOARD_PORT="$DASHBOARD_PORT" \
    CDI_PULL_POLICY="${CDI_PULL_POLICY:-always}" \
    COMPOSE_PROFILES="$PROFILE" \
    docker compose -f "$COMPOSE_FILE" "$@"
}

stop_all() {
  # Tear down both profiles so switching local ↔ remote is clean.
  env CDI_VERSION="$CDI_VERSION" COMPOSE_PROFILES=local,remote \
    docker compose -f "$COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true
  docker rm -f cdi-health-api cdi-health-dashboard >/dev/null 2>&1 || true
}

CMD=up
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
  up | down | reset)
    CMD="$1"
    shift
    ;;
  --build)
    BUILD=1
    shift
    ;;
  --bench)
    BENCH_IP="${2:-}"
    if [[ -z "$BENCH_IP" ]]; then
      echo "error: --bench requires an IP" >&2
      exit 1
    fi
    shift 2
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    ARGS+=("$1")
    shift
    ;;
  esac
done

if [[ -n "$BENCH_IP" ]]; then
  PROFILE=remote
fi

cd "$ROOT_DIR"

case "$CMD" in
up)
  ensure_env
  stop_all
  if [[ "$PROFILE" == "remote" ]]; then
    if [[ ! -f "$TEMPLATE" ]]; then
      echo "error: missing $TEMPLATE" >&2
      exit 1
    fi
    sed "s/__BENCH_HOST__/${BENCH_IP}/g" "$TEMPLATE" >"$GENERATED"
    echo "Remote bench mode — UI proxies API to http://${BENCH_IP}:8844"
  fi
  if [[ "$BUILD" == "1" ]]; then
    export CDI_PULL_POLICY=missing
    echo "Building images from source…"
    compose build
    compose up -d "${ARGS[@]+"${ARGS[@]}"}"
  else
    echo "Pulling ghcr.io/circulardrives/cdi-health-*:${CDI_VERSION}…"
    compose pull
    compose up -d "${ARGS[@]+"${ARGS[@]}"}"
  fi
  echo
  echo "CDI Health is up."
  echo "  Dashboard: http://127.0.0.1:${DASHBOARD_PORT}"
  if [[ "$PROFILE" == "local" ]]; then
    echo "  Health:    curl -s http://127.0.0.1:${DASHBOARD_PORT}/api/cdi/api/v1/health"
  else
    echo "  Bench API: http://${BENCH_IP}:8844 (via UI proxy)"
  fi
  echo "  Stop:      ./scripts/docker-up.sh down"
  ;;
down)
  stop_all
  echo "CDI Health Docker stack stopped."
  ;;
reset)
  stop_all
  docker volume rm cdi-health_cdi-api-data >/dev/null 2>&1 || true
  echo "CDI Health Docker stack reset (data volume removed)."
  ;;
*)
  usage >&2
  exit 1
  ;;
esac

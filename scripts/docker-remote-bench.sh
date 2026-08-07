#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_IP="${BENCH_IP:-}"
CDI_VERSION="${CDI_VERSION:-latest}"
GENERATED="$ROOT_DIR/deploy/docker/.nginx.remote-bench.generated.conf"
TEMPLATE="$ROOT_DIR/deploy/docker/nginx.remote-bench.conf.template"

usage() {
  cat <<USAGE
Usage: BENCH_IP=<bench-ip> ./scripts/docker-remote-bench.sh [compose args...]

Pin the dashboard to one remote grading bench — all API traffic (Discover, scans,
reports) is proxied to that host. Use this when scans must run on the bench itself.

For LAN discovery without hardcoding a bench IP, use:
  ./scripts/docker-lan-discover.sh

Environment:
  BENCH_IP       Required. Grading bench IP (e.g. 192.168.0.74)
  CDI_VERSION    GHCR tag (default: latest)
  DASHBOARD_PORT Host port for the UI (default: 3000)

Examples:
  BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh
  BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh down

Open http://127.0.0.1:\${DASHBOARD_PORT:-3000} — API calls go to http://\${BENCH_IP}:8844

Live scans are the default. Enable **Use mock data** on Discover for fixture demos.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$BENCH_IP" ]]; then
  echo "error: set BENCH_IP to pin API traffic to a remote bench" >&2
  echo "hint: for LAN discovery without BENCH_IP, run ./scripts/docker-lan-discover.sh" >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "error: missing template $TEMPLATE" >&2
  exit 1
fi

sed "s/__BENCH_HOST__/${BENCH_IP}/g" "$TEMPLATE" >"$GENERATED"

COMPOSE_FILES=(
  -f "$ROOT_DIR/deploy/docker/docker-compose.ghcr.yml"
  -f "$ROOT_DIR/deploy/docker/docker-compose.remote-bench.yml"
)

if [[ $# -eq 0 ]]; then
  set -- up -d
fi

cd "$ROOT_DIR"
echo "Remote bench mode — all API traffic → http://${BENCH_IP}:8844"
exec env CDI_VERSION="$CDI_VERSION" docker compose "${COMPOSE_FILES[@]}" "$@"

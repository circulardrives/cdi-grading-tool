#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH_IP="${BENCH_IP:-}"
CDI_VERSION="${CDI_VERSION:-0.9.4}"
GENERATED="$ROOT_DIR/deploy/docker/.nginx.remote-bench.generated.conf"
TEMPLATE="$ROOT_DIR/deploy/docker/nginx.remote-bench.conf.template"

usage() {
  cat <<USAGE
Usage: BENCH_IP=<bench-ip> ./scripts/docker-remote-bench.sh [compose args...]

Run the technician dashboard on this machine; all API traffic goes to the remote
grading bench (real drive scans, LAN discovery from the bench's network).

Environment:
  BENCH_IP       Required. Grading bench IP (e.g. 192.168.0.74)
  CDI_VERSION    GHCR tag (default: 0.9.4)
  DASHBOARD_PORT Host port for the UI (default: 3000)

Examples:
  BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh
  BENCH_IP=192.168.0.74 ./scripts/docker-remote-bench.sh down

Open http://127.0.0.1:\${DASHBOARD_PORT:-3000} → Discover with subnet 192.168.0.0/24
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$BENCH_IP" ]]; then
  echo "error: set BENCH_IP to the grading bench address (e.g. 192.168.0.74)" >&2
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
echo "Dashboard → http://${BENCH_IP}:8844 (bench API)"
exec env CDI_VERSION="$CDI_VERSION" docker compose "${COMPOSE_FILES[@]}" "$@"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CDI_VERSION="${CDI_VERSION:-0.9.5}"
CDI_DISCOVER_SUBNET="${CDI_DISCOVER_SUBNET:-192.168.0.0/24}"

COMPOSE_FILES=(
  -f "$ROOT_DIR/deploy/docker/docker-compose.ghcr.yml"
  -f "$ROOT_DIR/deploy/docker/docker-compose.lan-discover.yml"
)

usage() {
  cat <<USAGE
Usage: ./scripts/docker-lan-discover.sh [compose args...]

Run the technician dashboard + local API for LAN discovery. No BENCH_IP needed.

The API container probes explicit subnets you enter on the Discover page (works on
macOS Docker Desktop when you set the lab subnet, e.g. ${CDI_DISCOVER_SUBNET}).

Environment:
  CDI_VERSION          GHCR tag (default: 0.9.5)
  CDI_DISCOVER_SUBNET  Documented default subnet for Discover UI (default: 192.168.0.0/24)
  DASHBOARD_PORT       Host port for the UI (default: 3000)

Examples:
  ./scripts/docker-lan-discover.sh
  ./scripts/docker-lan-discover.sh down

Open http://127.0.0.1:\${DASHBOARD_PORT:-3000} → Discover → subnet ${CDI_DISCOVER_SUBNET}

Live scans are the default. Enable **Use mock data** on Discover for fixture demos.

To proxy all API traffic (including scans) to one remote bench, use:
  BENCH_IP=<bench-ip> ./scripts/docker-remote-bench.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -eq 0 ]]; then
  set -- up -d
elif [[ "${1:-}" == "down" ]]; then
  set -- down --remove-orphans "$@"
fi

cd "$ROOT_DIR"
echo "LAN discovery stack (no BENCH_IP)"
echo "  Dashboard: http://127.0.0.1:\${DASHBOARD_PORT:-3000}"
echo "  Discover subnet: ${CDI_DISCOVER_SUBNET} (enter on the Discover page)"
if [[ "${1:-}" == "up" ]]; then
  env CDI_VERSION="$CDI_VERSION" docker compose "${COMPOSE_FILES[@]}" "$@" ||
    env CDI_VERSION="$CDI_VERSION" docker compose "${COMPOSE_FILES[@]}" "$@"
else
  exec env CDI_VERSION="$CDI_VERSION" docker compose "${COMPOSE_FILES[@]}" "$@"
fi

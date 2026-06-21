#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<USAGE
Usage: ./scripts/docker-reset.sh [--clear-data]

Stop every CDI Health Docker overlay and remove leftover containers.

Use this when switching between mock demo, LAN discovery, host-network, or
remote-bench stacks and \`docker compose up\` fails with "No such container"
or "dependency failed to start".

Options:
  --clear-data  Also remove the API data volume (drops cached scan results)

Then start the stack you want, for example:
  CDI_VERSION=0.9.5 docker compose -f deploy/docker/docker-compose.ghcr.yml up -d --build
  ./scripts/docker-lan-discover.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

CLEAR_DATA=0
if [[ "${1:-}" == "--clear-data" ]]; then
  CLEAR_DATA=1
  shift
fi

COMPOSE_FILES=(
  -f "$ROOT_DIR/deploy/docker/docker-compose.ghcr.yml"
  -f "$ROOT_DIR/deploy/docker/docker-compose.host.yml"
  -f "$ROOT_DIR/deploy/docker/docker-compose.lan-discover.yml"
  -f "$ROOT_DIR/deploy/docker/docker-compose.remote-bench.yml"
)

cd "$ROOT_DIR"
docker compose "${COMPOSE_FILES[@]}" down --remove-orphans >/dev/null 2>&1 || true
docker rm -f cdi-health-api cdi-health-dashboard cdi-health-dashboard-proxy-1 >/dev/null 2>&1 || true

if [[ "$CLEAR_DATA" == "1" ]]; then
  docker volume rm cdi-health_cdi-api-data >/dev/null 2>&1 || true
  echo "Removed cdi-api-data volume (cached scans)."
fi

echo "CDI Health Docker stack reset complete."
echo "Tip: if mock fixture drives still appear after disabling mock mode, rerun with --clear-data."

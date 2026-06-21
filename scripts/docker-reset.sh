#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<USAGE
Usage: ./scripts/docker-reset.sh

Stop every CDI Health Docker overlay and remove leftover containers.

Use this when switching between mock demo, LAN discovery, host-network, or
remote-bench stacks and \`docker compose up\` fails with "No such container"
or "dependency failed to start".

Then start the stack you want, for example:
  CDI_VERSION=0.9.4 docker compose -f deploy/docker/docker-compose.ghcr.yml up -d
  ./scripts/docker-lan-discover.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
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

echo "CDI Health Docker stack reset complete."

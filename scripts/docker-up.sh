#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILES=(-f "$ROOT_DIR/deploy/docker/docker-compose.yml")

usage() {
  cat <<USAGE
Usage: ./scripts/docker-up.sh [options] [compose args...]

Start the CDI Health API + dashboard with Docker Compose (mock/demo by default).

Options:
  --hardware   Include hardware overlay for live drive scanning on the host
  --build      Pass --build to compose up
  -h, --help   Show this help

Examples:
  ./scripts/docker-up.sh --build
  ./scripts/docker-up.sh --hardware --build
  ./scripts/docker-up.sh down

Requires Docker Compose v2. Dashboard: http://127.0.0.1:\${DASHBOARD_PORT:-3000}
USAGE
}

HARDWARE=0
BUILD=0
COMPOSE_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
  --hardware)
    HARDWARE=1
    shift
    ;;
  --build)
    BUILD=1
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    COMPOSE_ARGS+=("$1")
    shift
    ;;
  esac
done

if [[ "$HARDWARE" == "1" ]]; then
  COMPOSE_FILES+=(-f "$ROOT_DIR/deploy/docker/docker-compose.hardware.yml")
fi

if [[ ${#COMPOSE_ARGS[@]} -eq 0 ]]; then
  COMPOSE_ARGS=(up)
  if [[ "$BUILD" == "1" ]]; then
    COMPOSE_ARGS+=(--build)
  fi
  COMPOSE_ARGS+=(-d)
fi

cd "$ROOT_DIR"
exec docker compose "${COMPOSE_FILES[@]}" "${COMPOSE_ARGS[@]}"

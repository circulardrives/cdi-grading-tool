#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.logs"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8844}"
DASHBOARD_HOST="${DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
API_TOKEN="${API_TOKEN:-localdevtoken}"
SKIP_INSTALL="${SKIP_INSTALL:-0}"
KILL_EXISTING_ON_PORT="${KILL_EXISTING_ON_PORT:-0}"

API_PID=""
DASHBOARD_PID=""

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

find_listeners_on_port() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    return 1
  fi

  lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

ensure_port_available() {
  local host="$1"
  local port="$2"
  local service_name="$3"
  local listeners

  listeners="$(find_listeners_on_port "$port")"
  if [[ -z "$listeners" ]]; then
    return 0
  fi

  if [[ "$KILL_EXISTING_ON_PORT" == "1" ]]; then
    echo "Port ${port} is in use; attempting to stop existing listener(s) for ${service_name}..."
    # shellcheck disable=SC2001
    echo "$listeners" | awk 'NR>1 {print $2}' | sort -u | while read -r pid; do
      if [[ -n "$pid" ]]; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
    sleep 1
    listeners="$(find_listeners_on_port "$port")"
    if [[ -z "$listeners" ]]; then
      return 0
    fi
  fi

  echo "Cannot start ${service_name}: ${host}:${port} is already in use." >&2
  echo "Current listener(s):" >&2
  echo "$listeners" >&2
  echo >&2
  echo "Stop existing process(es), or rerun with KILL_EXISTING_ON_PORT=1." >&2
  return 1
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local pid="${3:-}"
  local log_file="${4:-}"
  local attempts=120

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl not found; skipping readiness check for $name"
    return 0
  fi

  for _ in $(seq 1 "$attempts"); do
    if [[ -n "$pid" ]] && ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name process exited before readiness check completed." >&2
      if [[ -n "$log_file" ]] && [[ -f "$log_file" ]]; then
        echo "--- Last 120 lines of $log_file ---" >&2
        tail -n 120 "$log_file" >&2 || true
        echo "--- End of $log_file ---" >&2
      fi
      return 1
    fi

    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name is ready: $url"
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for $name at $url" >&2
  return 1
}

cleanup() {
  set +e
  if [[ -n "$DASHBOARD_PID" ]] && kill -0 "$DASHBOARD_PID" >/dev/null 2>&1; then
    kill "$DASHBOARD_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

require_cmd python3
require_cmd npm

mkdir -p "$LOG_DIR"

cd "$ROOT_DIR"

ensure_port_available "$API_HOST" "$API_PORT" "CDI API"
ensure_port_available "$DASHBOARD_HOST" "$DASHBOARD_PORT" "dashboard"

if [[ ! -d ".venv" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

if [[ "$SKIP_INSTALL" != "1" ]]; then
  echo "Installing Python API dependencies in .venv..."
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e '.[api]'

  echo "Installing dashboard dependencies..."
  npm --prefix dashboard install
else
  echo "Skipping dependency installation (SKIP_INSTALL=1)"
fi

cat > "$ROOT_DIR/dashboard/.env.local" <<ENV
CDI_API_BASE_URL=http://${API_HOST}:${API_PORT}
CDI_API_TOKEN=${API_TOKEN}
ENV

echo "Starting CDI API backend..."
(
  cd "$ROOT_DIR"
  PYTHONPATH=src .venv/bin/python -m cdi_health.api \
    --allow-non-root \
    --api-token "$API_TOKEN" \
    --host "$API_HOST" \
    --port "$API_PORT"
) >"$LOG_DIR/cdi-api.log" 2>&1 &
API_PID=$!

echo "Starting dashboard..."
(
  cd "$ROOT_DIR/dashboard"
  CDI_API_BASE_URL="http://${API_HOST}:${API_PORT}" CDI_API_TOKEN="$API_TOKEN" \
    npm run dev -- --hostname "$DASHBOARD_HOST" --port "$DASHBOARD_PORT"
) >"$LOG_DIR/cdi-dashboard.log" 2>&1 &
DASHBOARD_PID=$!

wait_for_http \
  "http://${API_HOST}:${API_PORT}/api/v1/health" \
  "CDI API" \
  "$API_PID" \
  "$LOG_DIR/cdi-api.log"

wait_for_http \
  "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}/api/cdi/api/v1/health" \
  "Dashboard proxy" \
  "$DASHBOARD_PID" \
  "$LOG_DIR/cdi-dashboard.log"

if command -v curl >/dev/null 2>&1; then
  echo "Running mock scan smoke checks..."

  curl -fsS -X POST "http://${API_HOST}:${API_PORT}/api/v1/scan" \
    -H "Content-Type: application/json" \
    -H "X-API-Token: ${API_TOKEN}" \
    -d '{"mock_data":"src/cdi_health/mock_data"}' >/dev/null

  curl -fsS -X POST "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}/api/cdi/api/v1/scan" \
    -H "Content-Type: application/json" \
    -d '{"mock_data":"src/cdi_health/mock_data"}' >/dev/null

  echo "Mock scan smoke checks passed."
fi

echo

echo "Services are running:"
echo "  API:       http://${API_HOST}:${API_PORT}"
echo "  Dashboard: http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
echo "  Logs:      $LOG_DIR/cdi-api.log, $LOG_DIR/cdi-dashboard.log"
echo
echo "Press Ctrl+C to stop both services."

while true; do
  sleep 2

  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "CDI API process exited unexpectedly. Check $LOG_DIR/cdi-api.log" >&2
    exit 1
  fi

  if ! kill -0 "$DASHBOARD_PID" >/dev/null 2>&1; then
    echo "Dashboard process exited unexpectedly. Check $LOG_DIR/cdi-dashboard.log" >&2
    exit 1
  fi
done

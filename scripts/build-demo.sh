#!/usr/bin/env bash
# Build the static public demo of the CDI Health dashboard (sample drives, no API).
#
#   ./scripts/build-demo.sh            # regenerate sample data, then build
#   ./scripts/build-demo.sh --no-data  # build from the committed sample data
#
# Output: dashboard/apps/web/dist-demo/ — plain static files (SPA fallback in
# SPA fallback via wrangler.demo.jsonc), ready for Cloudflare:
#
#   npx wrangler deploy -c dashboard/apps/web/wrangler.demo.jsonc
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/dashboard/apps/web"
REGENERATE=1

for arg in "$@"; do
  case "$arg" in
  --no-data) REGENERATE=0 ;;
  -h | --help)
    sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "error: unknown option: $arg" >&2
    exit 2
    ;;
  esac
done

if [[ "$REGENERATE" == 1 ]]; then
  PYTHON="${PYTHON:-}"
  if [[ -z "$PYTHON" ]]; then
    if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
      PYTHON="$ROOT_DIR/.venv/bin/python"
    else
      PYTHON="python3"
    fi
  fi
  echo "==> Generating sample data (real grader, anonymized fixtures)"
  (cd "$ROOT_DIR" && PYTHONPATH=src "$PYTHON" scripts/generate_demo_data.py)
fi

echo "==> Building the dashboard with VITE_DEMO=1"
cd "$ROOT_DIR/dashboard"
if [[ ! -d node_modules ]]; then
  bun install --frozen-lockfile
fi
cd "$WEB_DIR"
rm -rf dist-demo
VITE_DEMO=1 bun run build

echo
echo "Static demo ready: ${WEB_DIR#"$ROOT_DIR"/}/dist-demo"
echo "Preview:  bunx serve -s dashboard/apps/web/dist-demo"
echo "Deploy:   npx wrangler deploy -c dashboard/apps/web/wrangler.demo.jsonc"

#!/usr/bin/env bash
# Install-test a cdi-health .deb inside a throwaway Debian/Ubuntu container.
#
# Run from the repo root after building dist/cdi-health_*_all.deb (release.yml
# does this in CI for ubuntu:22.04 and debian:bookworm):
#
#   docker run --rm -v "$PWD:/work:ro" -w /work ubuntu:22.04 \
#     bash scripts/deb-smoke-test.sh [dist/cdi-health_X.Y.Z_all.deb]
#
# Checks: apt resolves Depends, postinst builds the venv (and fails the install
# if it cannot), CLI/API entry points work, a mock scan succeeds, and removal
# stops cleanly and deletes the generated venv.
set -euo pipefail

log() { printf '\n==> %s\n' "$*"; }

deb="${1:-}"
if [[ -z "$deb" ]]; then
  shopt -s nullglob
  debs=(dist/cdi-health_*_all.deb)
  shopt -u nullglob
  if [[ ${#debs[@]} -ne 1 ]]; then
    echo "error: expected exactly one dist/cdi-health_*_all.deb (found ${#debs[@]}); pass the path explicitly" >&2
    exit 1
  fi
  deb="${debs[0]}"
fi

export DEBIAN_FRONTEND=noninteractive
# shellcheck source=/dev/null
. /etc/os-release
log "Installing $(basename "$deb") on ${PRETTY_NAME}"

# Copy out of the read-only mount so apt's _apt sandbox user can read it.
cp "$deb" /tmp/
apt-get update -qq
apt-get install -y -qq --no-install-recommends "/tmp/$(basename "$deb")"

log "Entry points"
cdi-health --version
cdi-health-api --help >/dev/null
/opt/cdi-health/venv/bin/python -c 'import sys, cdi_health, fastapi, uvicorn; print("venv python", sys.version.split()[0])'

log "Mock scan"
mock_dir="$(/opt/cdi-health/venv/bin/python -c 'import os, cdi_health.mock_data as m; print(os.path.dirname(m.__file__))')"
cdi-health scan --mock-data "$mock_dir" -o json >/tmp/scan.json
python3 - <<'PY'
import json

with open("/tmp/scan.json") as fh:
    data = json.load(fh)
assert data, "mock scan returned no results"
print(f"mock scan ok ({len(data)} top-level entries)")
PY

log "Shipped examples"
test -f /usr/share/cdi-health/examples/systemd/cdi-health-api.service.d/lan.conf
test -f /usr/share/cdi-health/examples/cdi-health-api.env.example

log "Remove package"
apt-get remove -y -qq cdi-health
for path in /usr/local/bin/cdi-health /usr/local/bin/cdi-health-api /opt/cdi-health/venv; do
  if [[ -e "$path" ]]; then
    echo "error: ${path} still present after removal" >&2
    exit 1
  fi
done

log "deb smoke test passed on ${PRETTY_NAME}"

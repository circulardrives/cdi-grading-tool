#!/bin/sh
# cdi-health deb post-install: venv for system Python, host tools, systemd reload.
set -e

ROOT=/opt/cdi-health
WHEEL=$(ls "${ROOT}"/pkg/cdi_health-*.whl 2>/dev/null | head -1)

install_venv() {
  if [ -z "$WHEEL" ] || ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "cdi-health: python3-venv is required for cdi-health-api (e.g. apt install python3-venv)" >&2
    return 1
  fi

  if [ -x "${ROOT}/venv/bin/pip" ]; then
    "${ROOT}/venv/bin/pip" install -q --upgrade pip
    "${ROOT}/venv/bin/pip" install -q --upgrade "${WHEEL}[api]"
    return 0
  fi

  python3 -m venv "${ROOT}/venv"
  "${ROOT}/venv/bin/pip" install -q --upgrade pip
  "${ROOT}/venv/bin/pip" install -q "${WHEEL}[api]"
}

if [ -x "${ROOT}/scripts/install-host-dependencies.sh" ]; then
  "${ROOT}/scripts/install-host-dependencies.sh" --from-postinst || true
fi

install_venv || true

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload >/dev/null 2>&1 || true
fi

exit 0

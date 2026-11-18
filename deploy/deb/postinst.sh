#!/bin/sh
# cdi-health post-install (deb postinst / rpm %post).
#
# Builds /opt/cdi-health/venv from the bundled wheel + requirements-lock.txt,
# reloads systemd, and restarts cdi-health-api if it was already running (so an
# upgrade never leaves old code serving). Any failure aborts the install with a
# clear message instead of leaving a package whose commands cannot start.
#
# Dependencies are fetched with pip at install time. For air-gapped benches,
# point pip at a local wheelhouse or mirror via /etc/pip.conf, e.g.
#   [global]
#   no-index = true
#   find-links = /srv/wheelhouse
set -e

ROOT=/opt/cdi-health
VENV="${ROOT}/venv"
LOCK="${ROOT}/pkg/requirements-lock.txt"
UNIT=cdi-health-api.service

die() {
  echo "cdi-health: ERROR: $*" >&2
  echo "cdi-health: installation is incomplete. Fix the problem above, then re-run" >&2
  echo "cdi-health:   sudo dpkg --configure -a   (Debian/Ubuntu)  or reinstall the rpm." >&2
  exit 1
}

find_wheel() {
  for whl in "${ROOT}"/pkg/cdi_health-*.whl; do
    if [ -f "$whl" ]; then
      echo "$whl"
      return 0
    fi
  done
  return 1
}

python_minor() {
  "$1" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true
}

install_venv() {
  command -v python3 >/dev/null 2>&1 || die "python3 not found in PATH"
  wheel=$(find_wheel) || die "no bundled wheel found under ${ROOT}/pkg"
  [ -f "$LOCK" ] || die "missing ${LOCK}; cannot install reproducible dependencies"

  # Recreate the venv when missing, broken, or built for a different python3
  # (e.g. after a distribution upgrade replaced the system interpreter).
  sys_py=$(python_minor python3)
  venv_py=$(python_minor "${VENV}/bin/python")
  if [ -z "$venv_py" ] || [ "$venv_py" != "$sys_py" ] || [ ! -x "${VENV}/bin/pip" ]; then
    rm -rf "$VENV"
    python3 -m venv "$VENV" ||
      die "could not create ${VENV} with python3 ${sys_py} (Debian/Ubuntu: apt install python3-venv)"
  fi

  pip="${VENV}/bin/pip"
  "$pip" install -q --disable-pip-version-check --upgrade pip ||
    die "could not upgrade pip in ${VENV} (needs network access to PyPI or a mirror; see /etc/pip.conf)"
  # Locked runtime deps first, then the wheel itself without re-resolving.
  "$pip" install -q --disable-pip-version-check -r "$LOCK" ||
    die "could not install dependencies from ${LOCK} (needs network access to PyPI or a mirror; see /etc/pip.conf)"
  "$pip" install -q --disable-pip-version-check --no-deps --force-reinstall "$wheel" ||
    die "could not install ${wheel} into ${VENV}"

  "${VENV}/bin/python" -c 'import cdi_health' ||
    die "cdi_health does not import from ${VENV}"
}

install_venv

# The API token lives in this file; it must not be readable by other users.
ENV_FILE=/etc/default/cdi-health-api
if [ -f "$ENV_FILE" ] && [ -n "$(find "$ENV_FILE" -perm /077 2>/dev/null)" ]; then
  chmod 600 "$ENV_FILE" && chown root:root "$ENV_FILE" &&
    echo "cdi-health: note: tightened ${ENV_FILE} to mode 600 (it holds CDI_HEALTH_API_TOKEN)" >&2
fi

if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload || true
  # try-restart only restarts a unit that is already running: fresh installs
  # stay stopped until the operator enables it; upgrades pick up new code.
  if ! systemctl try-restart "$UNIT"; then
    echo "cdi-health: warning: ${UNIT} failed to restart; check: systemctl status ${UNIT}" >&2
  fi
fi

if ! command -v openSeaChest_Basics >/dev/null 2>&1; then
  echo "cdi-health: note: OpenSeaChest not found. For it (and sg3-utils / newer nvme-cli) run:" >&2
  echo "cdi-health:   sudo ${ROOT}/scripts/install-host-dependencies.sh --help" >&2
fi

exit 0

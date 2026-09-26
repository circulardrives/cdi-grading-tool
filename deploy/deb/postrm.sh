#!/bin/sh
# cdi-health post-removal (deb postrm / rpm %postun).
#
#   deb: $1 = remove | purge | upgrade | failed-upgrade | abort-install | abort-upgrade | disappear
#   rpm: $1 = 0 (erase) | >=1 (upgrade)
#
# Removes the venv that postinst generated (not tracked by the package
# manager). Scan state in /var/lib/cdi-health is kept, even on purge.
set -e

ROOT=/opt/cdi-health

case "$1" in
remove | purge | abort-install | disappear | 0)
  rm -rf "${ROOT}/venv"
  rmdir "${ROOT}/pkg" "${ROOT}/bin" "${ROOT}/scripts" "${ROOT}" 2>/dev/null || true
  if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload || true
  fi
  ;;
esac

exit 0

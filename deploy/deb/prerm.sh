#!/bin/sh
# cdi-health pre-removal (deb prerm / rpm %preun).
#
#   deb: $1 = remove | upgrade | deconfigure | failed-upgrade
#   rpm: $1 = 0 (erase) | >=1 (upgrade)
#
# On removal, stop and disable cdi-health-api so nothing keeps running (or
# restarts at boot) without its binaries. On upgrade, leave it alone: postinst
# restarts it once the new code is installed.
set -e

UNIT=cdi-health-api.service

case "$1" in
remove | deconfigure | 0) ;;
*) exit 0 ;;
esac

if [ -d /run/systemd/system ] && command -v systemctl >/dev/null 2>&1; then
  systemctl disable --now "$UNIT" >/dev/null 2>&1 || true
fi

exit 0

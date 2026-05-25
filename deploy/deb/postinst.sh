#!/bin/sh
# cdi-health deb post-install: ensure grading-host tools when apt can provide them.
set -e

if [ -x /opt/cdi-health/scripts/install-host-dependencies.sh ]; then
  /opt/cdi-health/scripts/install-host-dependencies.sh --from-postinst || true
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload >/dev/null 2>&1 || true
fi

exit 0

#!/bin/sh
# Fail fast when the API would bind a non-loopback interface without a token
# (unless lab no-auth mode is enabled with CDI_HEALTH_API_NO_AUTH=1).
set -eu

TOKEN="${CDI_HEALTH_API_TOKEN:-}"
NO_AUTH="${CDI_HEALTH_API_NO_AUTH:-0}"
HOST_ARG=""
PREV=""
for arg in "$@"; do
  if [ "$PREV" = "--host" ]; then
    HOST_ARG="$arg"
  fi
  PREV="$arg"
done

case "${HOST_ARG:-0.0.0.0}" in
127.0.0.1 | localhost | ::1) ;;
*)
  case "$NO_AUTH" in
  1 | true | TRUE | yes | YES | on | ON) ;;
  *)
    if [ -z "$TOKEN" ]; then
      echo "cdi-health-api: CDI_HEALTH_API_TOKEN is required when binding ${HOST_ARG:-0.0.0.0}" \
        "(or set CDI_HEALTH_API_NO_AUTH=1 on a trusted lab network)" >&2
      exit 1
    fi
    ;;
  esac
  ;;
esac

exec "$@"

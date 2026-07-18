#!/bin/sh
# Fail fast when the API would bind a non-loopback interface without a token.
set -eu

TOKEN="${CDI_HEALTH_API_TOKEN:-}"
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
  if [ -z "$TOKEN" ]; then
    echo "cdi-health-api: CDI_HEALTH_API_TOKEN is required when binding ${HOST_ARG:-0.0.0.0}" >&2
    exit 1
  fi
  ;;
esac

exec "$@"

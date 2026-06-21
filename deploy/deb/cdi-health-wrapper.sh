#!/bin/sh
# Shared launcher: prefer /opt/cdi-health/venv (system Python at install time).
ROOT=/opt/cdi-health

if [ -x "${ROOT}/venv/bin/python3" ]; then
  PYTHON="${ROOT}/venv/bin/python3"
elif [ -x "${ROOT}/venv/bin/python" ]; then
  PYTHON="${ROOT}/venv/bin/python"
else
  export PYTHONPATH="${ROOT}/lib${PYTHONPATH:+:${PYTHONPATH}}"
  PYTHON=python3
fi

exec "${PYTHON}" "$@"

#!/usr/bin/env bash
set -Eeuo pipefail

OVERRIDE_FILE="${OVERRIDE_FILE:-/opt/majlesyar_geodns/state/manual-override.json}"

if [[ -f "${OVERRIDE_FILE}" ]]; then
  rm -f "${OVERRIDE_FILE}"
fi

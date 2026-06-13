#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${ENV_FILE:-/etc/default/majlesyar-geo-probe}"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
fi

: "${SITE_CONFIG:?SITE_CONFIG is required}"
: "${REGION:?REGION is required}"
: "${JSON_OUTPUT:?JSON_OUTPUT is required}"
: "${PROM_OUTPUT:?PROM_OUTPUT is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/probe_runner.py" \
  --site-config "${SITE_CONFIG}" \
  --region "${REGION}" \
  --json-out "${JSON_OUTPUT}" \
  --prom-out "${PROM_OUTPUT}"

if [[ -n "${CONTROLLER_SSH_TARGET:-}" && -n "${CONTROLLER_STATE_DIR:-}" ]]; then
  ssh ${SSH_OPTIONS:-} "${CONTROLLER_SSH_TARGET}" "install -d -m 0750 '${CONTROLLER_STATE_DIR}'"
  scp ${SSH_OPTIONS:-} "${JSON_OUTPUT}" "${CONTROLLER_SSH_TARGET}:${CONTROLLER_STATE_DIR}/${REGION}.json"
fi

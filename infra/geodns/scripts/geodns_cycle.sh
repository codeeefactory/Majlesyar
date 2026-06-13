#!/usr/bin/env bash
set -Eeuo pipefail

ENV_FILE="${ENV_FILE:-/etc/default/majlesyar-geodns}"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
fi

: "${SITE_CONFIG:?SITE_CONFIG is required}"
: "${IRAN_PROBE_STATE:?IRAN_PROBE_STATE is required}"
: "${GLOBAL_PROBE_STATE:?GLOBAL_PROBE_STATE is required}"
: "${STATE_OUTPUT:?STATE_OUTPUT is required}"
: "${HISTORY_PATH:?HISTORY_PATH is required}"
: "${ZONE_OUTPUT:?ZONE_OUTPUT is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_STATE="$(mktemp)"
TMP_ZONE="$(mktemp)"
trap 'rm -f "${TMP_STATE}" "${TMP_ZONE}"' EXIT

python3 "${SCRIPT_DIR}/evaluate_failover.py" \
  --iran-probe "${IRAN_PROBE_STATE}" \
  --global-probe "${GLOBAL_PROBE_STATE}" \
  --output "${TMP_STATE}" \
  --history "${HISTORY_PATH}" \
  --manual-override "${MANUAL_OVERRIDE_PATH:-/opt/majlesyar_geodns/state/manual-override.json}"

python3 "${SCRIPT_DIR}/render_geo_zone.py" \
  --site-config "${SITE_CONFIG}" \
  --state "${TMP_STATE}" \
  --output "${TMP_ZONE}"

install -d "$(dirname "${STATE_OUTPUT}")" "$(dirname "${ZONE_OUTPUT}")"
cp "${TMP_STATE}" "${STATE_OUTPUT}"

if [[ ! -f "${ZONE_OUTPUT}" || ! cmp -s "${TMP_ZONE}" "${ZONE_OUTPUT}" ]]; then
  cp "${TMP_ZONE}" "${ZONE_OUTPUT}"
  if command -v pdns_control >/dev/null 2>&1; then
    pdns_control reload
  else
    systemctl reload pdns
  fi
fi

if [[ -n "${SECONDARY_SSH_TARGET:-}" && -n "${SECONDARY_ZONE_OUTPUT:-}" ]]; then
  ssh ${SSH_OPTIONS:-} "${SECONDARY_SSH_TARGET}" "install -d -m 0750 '$(dirname "${SECONDARY_ZONE_OUTPUT}")'"
  scp ${SSH_OPTIONS:-} "${ZONE_OUTPUT}" "${SECONDARY_SSH_TARGET}:${SECONDARY_ZONE_OUTPUT}"
  if [[ -n "${DNSSEC_KEYDIR:-}" && -n "${SECONDARY_DNSSEC_KEYDIR:-}" ]]; then
    ssh ${SSH_OPTIONS:-} "${SECONDARY_SSH_TARGET}" "install -d -m 0700 '${SECONDARY_DNSSEC_KEYDIR}'"
    rsync -az "${DNSSEC_KEYDIR}/" "${SECONDARY_SSH_TARGET}:${SECONDARY_DNSSEC_KEYDIR}/"
  fi
  ssh ${SSH_OPTIONS:-} "${SECONDARY_SSH_TARGET}" "pdns_control reload || systemctl reload pdns"
fi

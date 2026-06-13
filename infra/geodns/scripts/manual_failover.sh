#!/usr/bin/env bash
set -Eeuo pipefail

OVERRIDE_FILE="${OVERRIDE_FILE:-/opt/majlesyar_geodns/state/manual-override.json}"
IR_TARGET=""
DEFAULT_TARGET=""
REASON="manual override"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ir)
      IR_TARGET="$2"
      shift 2
      ;;
    --default)
      DEFAULT_TARGET="$2"
      shift 2
      ;;
    --reason)
      REASON="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${IR_TARGET}" || -z "${DEFAULT_TARGET}" ]]; then
  echo "Usage: $0 --ir <iran|global|maintenance> --default <iran|global|maintenance> [--reason TEXT]" >&2
  exit 1
fi

mkdir -p "$(dirname "${OVERRIDE_FILE}")"
cat > "${OVERRIDE_FILE}" <<EOF
{
  "enabled": true,
  "updated_at": "$(date -u +%FT%TZ)",
  "reason": ${REASON@Q},
  "policy": {
    "iran": "${IR_TARGET}",
    "default": "${DEFAULT_TARGET}"
  }
}
EOF

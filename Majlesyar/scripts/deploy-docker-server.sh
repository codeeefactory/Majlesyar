#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.prod.yml}"
PROJECT_NAME="${PROJECT_NAME:-majlesyar}"

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy][error] %s\n' "$*" >&2
  exit 1
}

compose() {
  docker compose --project-name "${PROJECT_NAME}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

require_docker() {
  command -v docker >/dev/null 2>&1 || fail "Docker is not installed."
  docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is not installed."
}

prepare_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    return
  fi

  cp "${ROOT_DIR}/.env.production.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}" || true
  fail "Created ${ENV_FILE}. Edit secrets/domains, then run this script again."
}

pull_latest_if_repo() {
  if [[ "${SKIP_GIT_PULL:-0}" == "1" || ! -d "${ROOT_DIR}/.git" ]]; then
    return
  fi

  log "Pulling latest git changes..."
  git -C "${ROOT_DIR}" pull --ff-only
}

deploy() {
  log "Building and starting production stack..."
  compose up -d --build --remove-orphans
}

wait_health() {
  log "Waiting for app health..."
  for _ in $(seq 1 60); do
    if compose exec -T app python - <<'PY' >/dev/null 2>&1
import json
import sys
import urllib.request

response = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health/", timeout=4)
payload = json.load(response)
sys.exit(0 if response.status == 200 and payload.get("ok") else 1)
PY
    then
      log "App healthy."
      return
    fi
    sleep 2
  done

  compose logs --tail=120 app || true
  fail "App did not become healthy."
}

show_result() {
  local host_port
  host_port="$(grep -E '^HOST_PORT=' "${ENV_FILE}" | tail -1 | cut -d= -f2- || true)"
  host_port="${host_port:-80}"

  log "Deploy complete."
  log "Local check: http://127.0.0.1:${host_port}/api/v1/health/"
  log "Logs: docker compose --env-file ${ENV_FILE} -f ${COMPOSE_FILE} logs -f app"
}

main() {
  require_docker
  prepare_env
  pull_latest_if_repo
  deploy
  wait_health
  show_result
}

main "$@"

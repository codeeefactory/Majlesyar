#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-majlesyar}"
IMAGE_NAME="${IMAGE_NAME:-${APP_NAME}:latest}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-Dockerfile}"
DOCKER_BUILD_PULL="${DOCKER_BUILD_PULL:-false}"
CONTAINER_NAME="${CONTAINER_NAME:-${APP_NAME}}"
BOT_CONTAINER_NAME="${BOT_CONTAINER_NAME:-${APP_NAME}-telegram-bot}"
HOST_PORT="${HOST_PORT:-80}"
APP_PORT="${APP_PORT:-8000}"
CPU_LIMIT="${CPU_LIMIT:-2.0}"
MEMORY_LIMIT="${MEMORY_LIMIT:-2g}"
MEMORY_SWAP_LIMIT="${MEMORY_SWAP_LIMIT:-2g}"
DOMAIN="${DOMAIN:-}"
PUBLIC_URL="${PUBLIC_URL:-}"
APT_USE_IRAN_MIRROR="${APT_USE_IRAN_MIRROR:-0}"
REPO_URL="${REPO_URL:-https://github.com/codeeefactory/Majlesyar.git}"
REPO_REF="${REPO_REF:-master}"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-0}"
BOOTSTRAP_DIR="${BOOTSTRAP_DIR:-/opt/majlesyar-src}"
PROJECT_SUBDIR="${PROJECT_SUBDIR:-Majlesyar}"
DATA_DIR="${DATA_DIR:-}"

ADMIN_USERNAME="${ADMIN_USERNAME:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
TELEGRAM_BOT_ENABLED="${TELEGRAM_BOT_ENABLED:-0}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_BOT_USE_WEBHOOK="${TELEGRAM_BOT_USE_WEBHOOK:-1}"
TELEGRAM_BOT_WEBHOOK_SECRET="${TELEGRAM_BOT_WEBHOOK_SECRET:-}"
TELEGRAM_BOT_WEBHOOK_PATH="${TELEGRAM_BOT_WEBHOOK_PATH:-api/v1/telegram/webhook/}"
TELEGRAM_BOT_ALLOWED_USER_IDS="${TELEGRAM_BOT_ALLOWED_USER_IDS:-}"
TELEGRAM_BOT_ALLOWED_CHAT_IDS="${TELEGRAM_BOT_ALLOWED_CHAT_IDS:-}"
TELEGRAM_BOT_ADMIN_ONLY="${TELEGRAM_BOT_ADMIN_ONLY:-1}"
TELEGRAM_BOT_NOTIFICATIONS_ENABLED="${TELEGRAM_BOT_NOTIFICATIONS_ENABLED:-0}"
BOT_POLL_TIMEOUT="${BOT_POLL_TIMEOUT:-5}"
BOT_SLEEP_SECONDS="${BOT_SLEEP_SECONDS:-5}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR=""
ENV_FILE=""
DB_FILE=""
MEDIA_DIR=""

log() {
  printf '[startup] %s\n' "$*"
}

fail() {
  printf '[startup][error] %s\n' "$*" >&2
  exit 1
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "This step needs root privileges. Install sudo or run as root."
  fi
}

require_linux() {
  local os
  os="$(uname -s)"
  [[ "${os}" == "Linux" ]] || fail "This script must run on Linux (detected: ${os})."
}

set_runtime_paths() {
  if [[ -n "${DATA_DIR}" ]]; then
    DEPLOY_DIR="${DATA_DIR}"
  else
    DEPLOY_DIR="${ROOT_DIR}/.deploy"
  fi
  ENV_FILE="${DEPLOY_DIR}/.env.production"
  DB_FILE="${DEPLOY_DIR}/db.sqlite3"
  MEDIA_DIR="${DEPLOY_DIR}/media"
}

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    fail "git is required but apt-get is unavailable on this system."
  fi

  log "git not found. Installing git..."
  run_root apt-get update
  run_root apt-get install -y git ca-certificates
}

ensure_runtime_tools() {
  local packages=()
  command -v curl >/dev/null 2>&1 || packages+=(curl)
  command -v openssl >/dev/null 2>&1 || packages+=(openssl)

  if [[ ${#packages[@]} -eq 0 ]]; then
    return
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    fail "Missing required tools: ${packages[*]}."
  fi

  run_root apt-get update
  run_root apt-get install -y "${packages[@]}"
}

is_repo_layout() {
  [[ -f "${ROOT_DIR}/Dockerfile" && -d "${ROOT_DIR}/backend" ]]
}

bootstrap_repo_if_needed() {
  is_repo_layout && return

  [[ -n "${REPO_URL}" ]] || fail \
    "Dockerfile/backend not found in ${ROOT_DIR}. For first-boot startup usage set REPO_URL (and optionally PROJECT_SUBDIR/REPO_REF)."

  ensure_git
  log "Project files not found in script directory. Bootstrapping from ${REPO_URL} ..."

  run_root mkdir -p "$(dirname "${BOOTSTRAP_DIR}")"

  if [[ -d "${BOOTSTRAP_DIR}/.git" ]]; then
    run_root git -C "${BOOTSTRAP_DIR}" fetch --all --tags
    run_root git -C "${BOOTSTRAP_DIR}" checkout "${REPO_REF}"
    run_root git -C "${BOOTSTRAP_DIR}" pull --ff-only origin "${REPO_REF}"
  else
    run_root rm -rf "${BOOTSTRAP_DIR}"
    run_root git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" "${BOOTSTRAP_DIR}"
  fi

  local candidate_root="${BOOTSTRAP_DIR}"
  if [[ -n "${PROJECT_SUBDIR}" ]]; then
    candidate_root="${BOOTSTRAP_DIR}/${PROJECT_SUBDIR}"
  fi

  [[ -f "${candidate_root}/Dockerfile" ]] || fail \
    "Dockerfile not found after clone. Checked: ${candidate_root}/Dockerfile"
  [[ -d "${candidate_root}/backend" ]] || fail \
    "backend/ not found after clone. Checked: ${candidate_root}/backend"

  ROOT_DIR="${candidate_root}"
  log "Using project directory: ${ROOT_DIR}"
}

ensure_repo_layout() {
  bootstrap_repo_if_needed
  [[ -f "${ROOT_DIR}/Dockerfile" ]] || fail "Dockerfile not found in ${ROOT_DIR}."
  [[ -d "${ROOT_DIR}/backend" ]] || fail "backend/ not found in ${ROOT_DIR}."
}

pull_latest_if_repo() {
  [[ "${SKIP_GIT_PULL}" != "1" ]] || {
    log "Skipping git update (SKIP_GIT_PULL=1)."
    return
  }
  [[ -d "${ROOT_DIR}/.git" ]] || return

  if [[ -n "$(git -C "${ROOT_DIR}" status --porcelain --untracked-files=no)" ]]; then
    fail "Tracked local changes found in ${ROOT_DIR}; refusing to pull. Commit/stash them or set SKIP_GIT_PULL=1."
  fi

  log "Pulling latest source for ${REPO_REF} ..."
  git -C "${ROOT_DIR}" fetch origin "${REPO_REF}"
  git -C "${ROOT_DIR}" checkout "${REPO_REF}"
  git -C "${ROOT_DIR}" pull --ff-only origin "${REPO_REF}"
}

configure_apt_iran_mirrors() {
  [[ "${APT_USE_IRAN_MIRROR}" == "1" ]] || {
    log "Skipping Iranian APT mirrors (APT_USE_IRAN_MIRROR=${APT_USE_IRAN_MIRROR})."
    return
  }

  if ! command -v apt-get >/dev/null 2>&1; then
    log "APT not found; skipping update."
    return
  fi

  log "Updating APT..."
  run_root apt-get update
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi

  log "Docker not found. Installing Docker Engine..."

  if ! command -v curl >/dev/null 2>&1; then
    run_root apt-get update
    run_root apt-get install -y curl
  fi

  if [[ "${EUID}" -eq 0 ]]; then
    sh -c "$(curl -fsSL https://get.docker.com)"
  else
    curl -fsSL https://get.docker.com | sudo sh
  fi

  if command -v systemctl >/dev/null 2>&1; then
    run_root systemctl enable --now docker
  fi
}

generate_secret_key() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 48
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
    return
  fi

  fail "Cannot generate DJANGO_SECRET_KEY automatically (need openssl or python3)."
}

env_is_truthy() {
  local value="${1:-}"
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
  [[ "${value}" == "1" || "${value}" == "true" || "${value}" == "yes" || "${value}" == "on" ]]
}

env_file_get() {
  local key="$1"
  [[ -f "${ENV_FILE}" ]] || return 0
  awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, "", $0); print $0; exit }' "${ENV_FILE}"
}

env_file_set() {
  local key="$1"
  local value="$2"
  if [[ -f "${ENV_FILE}" ]] && grep -q "^${key}=" "${ENV_FILE}"; then
    local tmp_file
    tmp_file="$(mktemp)"
    awk -F= -v key="${key}" -v value="${value}" 'BEGIN { written = 0 } $1 == key { print key "=" value; written = 1; next } { print } END { if (!written) print key "=" value }' "${ENV_FILE}" > "${tmp_file}"
    cat "${tmp_file}" > "${ENV_FILE}"
    rm -f "${tmp_file}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

build_allowed_hosts() {
  local ip host_list public_host domain_host
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  host_list="localhost,127.0.0.1"
  if [[ -n "${ip}" ]]; then
    host_list="${host_list},${ip}"
  fi
  if [[ -n "${DOMAIN}" ]]; then
    domain_host="${DOMAIN#http://}"
    domain_host="${domain_host#https://}"
    domain_host="${domain_host%%/*}"
    domain_host="${domain_host%%:*}"
    host_list="${host_list},${domain_host},www.${domain_host}"
  fi
  if [[ -n "${PUBLIC_URL}" ]]; then
    public_host="${PUBLIC_URL#http://}"
    public_host="${public_host#https://}"
    public_host="${public_host%%/*}"
    public_host="${public_host%%:*}"
    if [[ -n "${public_host}" ]]; then
      host_list="${host_list},${public_host},www.${public_host}"
    fi
  fi
  printf '%s' "${host_list}" | tr ',' '\n' | awk 'NF && !seen[$0]++' | paste -sd, -
}

build_public_url() {
  if [[ -n "${PUBLIC_URL}" ]]; then
    printf '%s' "${PUBLIC_URL}"
    return
  fi

  if [[ -n "${DOMAIN}" ]]; then
    printf 'https://%s' "${DOMAIN}"
    return
  fi

  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -n "${ip}" ]]; then
    printf 'http://%s:%s' "${ip}" "${HOST_PORT}"
  else
    printf 'http://localhost:%s' "${HOST_PORT}"
  fi
}

write_env_file() {
  mkdir -p "${DEPLOY_DIR}" "${MEDIA_DIR}"
  touch "${DB_FILE}"

  local secret_key allowed_hosts public_url
  secret_key="${DJANGO_SECRET_KEY:-$(env_file_get DJANGO_SECRET_KEY)}"
  if [[ -z "${secret_key}" ]]; then
    secret_key="$(generate_secret_key)"
  fi
  allowed_hosts="$(build_allowed_hosts)"
  public_url="$(build_public_url)"

  umask 077
  touch "${ENV_FILE}"
  env_file_set "PORT" "${APP_PORT}"
  env_file_set "DJANGO_DEBUG" "0"
  env_file_set "DJANGO_SECRET_KEY" "${secret_key}"
  env_file_set "DJANGO_ALLOWED_HOSTS" "${allowed_hosts}"
  env_file_set "DJANGO_MEDIA_ROOT" "/app/media"
  env_file_set "CORS_ALLOWED_ORIGINS" "${public_url}"
  env_file_set "CSRF_TRUSTED_ORIGINS" "${public_url}"
  env_file_set "TELEGRAM_BOT_ENABLED" "${TELEGRAM_BOT_ENABLED}"
  env_file_set "TELEGRAM_BOT_TOKEN" "${TELEGRAM_BOT_TOKEN}"
  env_file_set "TELEGRAM_BOT_USE_WEBHOOK" "${TELEGRAM_BOT_USE_WEBHOOK}"
  env_file_set "TELEGRAM_BOT_WEBHOOK_SECRET" "${TELEGRAM_BOT_WEBHOOK_SECRET}"
  env_file_set "TELEGRAM_BOT_WEBHOOK_PATH" "${TELEGRAM_BOT_WEBHOOK_PATH}"
  env_file_set "TELEGRAM_BOT_BASE_URL" "${public_url}"
  env_file_set "TELEGRAM_BOT_ALLOWED_USER_IDS" "${TELEGRAM_BOT_ALLOWED_USER_IDS}"
  env_file_set "TELEGRAM_BOT_ALLOWED_CHAT_IDS" "${TELEGRAM_BOT_ALLOWED_CHAT_IDS}"
  env_file_set "TELEGRAM_BOT_ADMIN_ONLY" "${TELEGRAM_BOT_ADMIN_ONLY}"
  env_file_set "TELEGRAM_BOT_NOTIFICATIONS_ENABLED" "${TELEGRAM_BOT_NOTIFICATIONS_ENABLED}"
  umask 022
}

build_image() {
  local dockerfile="${DOCKERFILE_PATH}"
  if [[ "${dockerfile}" != /* ]]; then
    dockerfile="${ROOT_DIR}/${dockerfile}"
  fi
  [[ -f "${dockerfile}" ]] || fail "Dockerfile not found: ${dockerfile}"

  log "Building image ${IMAGE_NAME} ..."
  docker build --pull="${DOCKER_BUILD_PULL}" -f "${dockerfile}" -t "${IMAGE_NAME}" "${ROOT_DIR}"
}

start_container() {
  log "Starting container ${CONTAINER_NAME} ..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --cpus "${CPU_LIMIT}" \
    --memory "${MEMORY_LIMIT}" \
    --memory-swap "${MEMORY_SWAP_LIMIT}" \
    --env-file "${ENV_FILE}" \
    -p "${HOST_PORT}:${APP_PORT}" \
    -v "${DB_FILE}:/app/db.sqlite3" \
    -v "${MEDIA_DIR}:/app/media" \
    "${IMAGE_NAME}" >/dev/null
}

wait_for_container() {
  local health_url="http://127.0.0.1:${HOST_PORT}/api/v1/health/"
  if [[ "${HOST_PORT}" == *:* ]]; then
    local bind_host="${HOST_PORT%:*}"
    local bind_port="${HOST_PORT##*:}"
    if [[ "${bind_host}" == "0.0.0.0" || "${bind_host}" == "::" || "${bind_host}" == "[::]" ]]; then
      bind_host="127.0.0.1"
    fi
    health_url="http://${bind_host}:${bind_port}/api/v1/health/"
  fi

  log "Waiting for application health at ${health_url} ..."
  for _ in $(seq 1 60); do
    if curl --fail --silent --show-error --max-time 3 "${health_url}" >/dev/null 2>&1; then
      log "Application is healthy."
      return
    fi
    sleep 2
  done

  docker logs --tail 100 "${CONTAINER_NAME}" || true
  fail "Application did not become healthy in time."
}

create_superuser_if_requested() {
  if [[ -z "${ADMIN_USERNAME}" || -z "${ADMIN_PASSWORD}" ]]; then
    log "Skipping superuser creation (set ADMIN_USERNAME and ADMIN_PASSWORD to enable)."
    return
  fi

  log "Creating/updating Django superuser ${ADMIN_USERNAME} ..."
  docker exec \
    -e DJANGO_SUPERUSER_USERNAME="${ADMIN_USERNAME}" \
    -e DJANGO_SUPERUSER_EMAIL="${ADMIN_EMAIL}" \
    -e DJANGO_SUPERUSER_PASSWORD="${ADMIN_PASSWORD}" \
    "${CONTAINER_NAME}" \
    python manage.py shell -c "exec(\"\"\"from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ['DJANGO_SUPERUSER_USERNAME']
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
user, created = User.objects.get_or_create(
    username=username,
    defaults={'email': email, 'is_staff': True, 'is_superuser': True},
)
changed = False
if user.email != email:
    user.email = email
    changed = True
if not user.is_staff:
    user.is_staff = True
    changed = True
if not user.is_superuser:
    user.is_superuser = True
    changed = True
if created or not user.check_password(password):
    user.set_password(password)
    changed = True
if changed:
    user.save()
print('superuser ready')
\"\"\")"
}

configure_telegram_bot_if_requested() {
  docker rm -f "${BOT_CONTAINER_NAME}" >/dev/null 2>&1 || true

  if ! env_is_truthy "$(env_file_get TELEGRAM_BOT_ENABLED)"; then
    log "Telegram bot disabled."
    return
  fi
  if [[ -z "$(env_file_get TELEGRAM_BOT_TOKEN)" ]]; then
    log "Telegram bot enabled but TELEGRAM_BOT_TOKEN is empty; skipping bot startup."
    return
  fi

  if env_is_truthy "$(env_file_get TELEGRAM_BOT_USE_WEBHOOK)"; then
    log "Configuring Telegram webhook ..."
    docker exec "${CONTAINER_NAME}" python manage.py configure_telegram_webhook
    return
  fi

  log "Starting Telegram polling container ${BOT_CONTAINER_NAME} ..."
  docker exec "${CONTAINER_NAME}" python manage.py configure_telegram_webhook --delete >/dev/null 2>&1 || true
  docker run -d \
    --name "${BOT_CONTAINER_NAME}" \
    --restart unless-stopped \
    --env-file "${ENV_FILE}" \
    -v "${DB_FILE}:/app/db.sqlite3" \
    -v "${MEDIA_DIR}:/app/media" \
    "${IMAGE_NAME}" \
    sh -c "python manage.py migrate --noinput && python manage.py run_telegram_bot --poll-timeout ${BOT_POLL_TIMEOUT} --sleep-seconds ${BOT_SLEEP_SECONDS}" >/dev/null
}

print_result() {
  local public_url
  public_url="$(build_public_url)"

  log "Deployment complete."
  log "Container: ${CONTAINER_NAME}"
  if env_is_truthy "$(env_file_get TELEGRAM_BOT_ENABLED)"; then
    log "Telegram bot: enabled"
  fi
  log "URL: ${public_url}"
  log "Admin: ${public_url}/majmanage/"
  log "Swagger: ${public_url}/api/docs/"
  log "Logs: docker logs -f ${CONTAINER_NAME}"
}

main() {
  require_linux
  configure_apt_iran_mirrors
  ensure_repo_layout
  pull_latest_if_repo
  set_runtime_paths
  ensure_runtime_tools
  ensure_docker
  write_env_file
  build_image
  start_container
  wait_for_container
  create_superuser_if_requested
  configure_telegram_bot_if_requested
  print_result
}

main "$@"

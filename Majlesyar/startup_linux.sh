#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-majlesyar}"
IMAGE_NAME="${IMAGE_NAME:-${APP_NAME}:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-${APP_NAME}}"
HOST_PORT="${HOST_PORT:-80}"
APP_PORT="${APP_PORT:-8000}"
DOMAIN="${DOMAIN:-}"
PUBLIC_URL="${PUBLIC_URL:-}"
APT_USE_IRAN_MIRROR="${APT_USE_IRAN_MIRROR:-1}"
IRAN_UBUNTU_MIRROR="${IRAN_UBUNTU_MIRROR:-https://repo.linuxmirrors.ir/ubuntu}"
IRAN_DEBIAN_MIRROR="${IRAN_DEBIAN_MIRROR:-https://archive.debian.petiak.ir/debian}"

ADMIN_USERNAME="${ADMIN_USERNAME:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${ROOT_DIR}/.deploy"
ENV_FILE="${DEPLOY_DIR}/.env.production"
DB_FILE="${DEPLOY_DIR}/db.sqlite3"
MEDIA_DIR="${DEPLOY_DIR}/media"

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

ensure_repo_layout() {
  [[ -f "${ROOT_DIR}/Dockerfile" ]] || fail "Dockerfile not found in ${ROOT_DIR}."
  [[ -d "${ROOT_DIR}/backend" ]] || fail "backend/ not found in ${ROOT_DIR}."
}

configure_apt_iran_mirrors() {
  [[ "${APT_USE_IRAN_MIRROR}" == "1" ]] || {
    log "Skipping Iranian APT mirrors (APT_USE_IRAN_MIRROR=${APT_USE_IRAN_MIRROR})."
    return
  }

  if ! command -v apt-get >/dev/null 2>&1; then
    log "APT not found; skipping mirror configuration."
    return
  fi

  if [[ ! -f /etc/os-release ]]; then
    log "/etc/os-release not found; skipping mirror configuration."
    return
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  local distro="${ID:-}"
  local backup_dir="/etc/apt/backup-startup-$(date +%Y%m%d%H%M%S)"
  local source_file

  run_root mkdir -p "${backup_dir}"

  case "${distro}" in
    ubuntu)
      log "Switching Ubuntu APT repos to Iranian mirror: ${IRAN_UBUNTU_MIRROR}"
      for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
        [[ -f "${source_file}" ]] || continue
        run_root cp "${source_file}" "${backup_dir}/"
        run_root sed -i -E \
          -e "s#https?://([a-z]{2}\\.)?archive\\.ubuntu\\.com/ubuntu/?#${IRAN_UBUNTU_MIRROR}/#g" \
          -e "s#https?://security\\.ubuntu\\.com/ubuntu/?#${IRAN_UBUNTU_MIRROR}/#g" \
          -e "s#https?://ir\\.archive\\.ubuntu\\.com/ubuntu/?#${IRAN_UBUNTU_MIRROR}/#g" \
          -e "s#https?://ports\\.ubuntu\\.com/ubuntu-ports/?#${IRAN_UBUNTU_MIRROR}/#g" \
          "${source_file}"
      done
      ;;
    debian)
      log "Switching Debian APT repos to Iranian mirror: ${IRAN_DEBIAN_MIRROR}"
      for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
        [[ -f "${source_file}" ]] || continue
        run_root cp "${source_file}" "${backup_dir}/"
        run_root sed -i -E \
          -e "s#https?://deb\\.debian\\.org/debian/?#${IRAN_DEBIAN_MIRROR}/#g" \
          -e "s#https?://ftp\\.debian\\.org/debian/?#${IRAN_DEBIAN_MIRROR}/#g" \
          -e "s#https?://httpredir\\.debian\\.org/debian/?#${IRAN_DEBIAN_MIRROR}/#g" \
          "${source_file}"
      done
      ;;
    *)
      log "Distro '${distro}' not targeted for automatic APT mirror rewrite."
      return
      ;;
  esac

  log "APT mirror backups are stored in ${backup_dir}"
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

build_allowed_hosts() {
  local ip host_list
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  host_list="localhost,127.0.0.1"
  if [[ -n "${ip}" ]]; then
    host_list="${host_list},${ip}"
  fi
  if [[ -n "${DOMAIN}" ]]; then
    host_list="${host_list},${DOMAIN}"
  fi
  printf '%s' "${host_list}"
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
  secret_key="${DJANGO_SECRET_KEY:-$(generate_secret_key)}"
  allowed_hosts="$(build_allowed_hosts)"
  public_url="$(build_public_url)"

  umask 077
  cat > "${ENV_FILE}" <<EOF
PORT=${APP_PORT}
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=${secret_key}
DJANGO_ALLOWED_HOSTS=${allowed_hosts}
CORS_ALLOWED_ORIGINS=${public_url}
CSRF_TRUSTED_ORIGINS=${public_url}
EOF
  umask 022
}

build_image() {
  log "Building image ${IMAGE_NAME} ..."
  docker build -t "${IMAGE_NAME}" "${ROOT_DIR}"
}

start_container() {
  log "Starting container ${CONTAINER_NAME} ..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --env-file "${ENV_FILE}" \
    -p "${HOST_PORT}:${APP_PORT}" \
    -v "${DB_FILE}:/app/db.sqlite3" \
    -v "${MEDIA_DIR}:/app/media" \
    "${IMAGE_NAME}" >/dev/null
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
    python manage.py createsuperuser --noinput || true
}

print_result() {
  local public_url
  public_url="$(build_public_url)"

  log "Deployment complete."
  log "Container: ${CONTAINER_NAME}"
  log "URL: ${public_url}"
  log "Admin: ${public_url}/admin/"
  log "Swagger: ${public_url}/api/docs/"
  log "Logs: docker logs -f ${CONTAINER_NAME}"
}

main() {
  require_linux
  ensure_repo_layout
  configure_apt_iran_mirrors
  ensure_docker
  write_env_file
  build_image
  start_container
  create_superuser_if_requested
  print_result
}

main "$@"

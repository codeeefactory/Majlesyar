<<<<<<< HEAD
#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-majlesyar}"
IMAGE_NAME="${IMAGE_NAME:-${APP_NAME}:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-${APP_NAME}}"
HOST_PORT="${HOST_PORT:-80}"
APP_PORT="${APP_PORT:-8000}"
CPU_LIMIT="${CPU_LIMIT:-2.0}"
MEMORY_LIMIT="${MEMORY_LIMIT:-2g}"
MEMORY_SWAP_LIMIT="${MEMORY_SWAP_LIMIT:-2g}"
DOMAIN="${DOMAIN:-}"
PUBLIC_URL="${PUBLIC_URL:-}"
APT_USE_IRAN_MIRROR="${APT_USE_IRAN_MIRROR:-0}"
REPO_URL="${REPO_URL:-https://github.com/codeeefactory/Majlesyar.git}"
REPO_REF="${REPO_REF:-main}"
BOOTSTRAP_DIR="${BOOTSTRAP_DIR:-/opt/majlesyar-src}"
PROJECT_SUBDIR="${PROJECT_SUBDIR:-Majlesyar}"

ADMIN_USERNAME="${ADMIN_USERNAME:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

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
  DEPLOY_DIR="${ROOT_DIR}/.deploy"
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
    run_root git -C "${BOOTSTRAP_DIR}" checkout main
    run_root git -C "${BOOTSTRAP_DIR}" pull --ff-only origin main
  else
    run_root rm -rf "${BOOTSTRAP_DIR}"
    run_root git clone --depth 1 --branch main "${REPO_URL}" "${BOOTSTRAP_DIR}"
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
    --cpus "${CPU_LIMIT}" \
    --memory "${MEMORY_LIMIT}" \
    --memory-swap "${MEMORY_SWAP_LIMIT}" \
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
  configure_apt_iran_mirrors
  ensure_repo_layout
  set_runtime_paths
  ensure_docker
  write_env_file
  build_image
  start_container
  create_superuser_if_requested
  print_result
}

main "$@"
=======
--- /mnt/data/startup_linux_with_tls.sh	2026-03-21 11:07:27.450071590 +0000
+++ /mnt/data/startup_linux_with_apache_tls.sh	2026-03-21 11:09:09.470521990 +0000
@@ -26,7 +26,7 @@
 TLS_SERVER_NAME="${TLS_SERVER_NAME:-${DOMAIN}}"
 CERT_INSTALL_DIR="${CERT_INSTALL_DIR:-/etc/ssl/${APP_NAME}}"
 CERT_PFX_PASSWORD="${CERT_PFX_PASSWORD:-}"
-NGINX_SITE_NAME="${NGINX_SITE_NAME:-${APP_NAME}}"
+APACHE_SITE_NAME="${APACHE_SITE_NAME:-${APP_NAME}}"
 PROXY_HTTP_PORT="${PROXY_HTTP_PORT:-80}"
 PROXY_HTTPS_PORT="${PROXY_HTTPS_PORT:-443}"
 APP_BIND_HOST="${APP_BIND_HOST:-127.0.0.1}"
@@ -219,7 +219,7 @@
 }
 
 ensure_tls_dependencies() {
-  ensure_packages unzip openssl nginx ca-certificates
+  ensure_packages unzip openssl apache2 ca-certificates
 }
 
 extract_first_match() {
@@ -406,62 +406,90 @@
     "${IMAGE_NAME}" >/dev/null
 }
 
-write_nginx_config() {
-  (( TLS_ACTIVE )) || return
+apache_server_aliases() {
+  local aliases=()
+
+  if [[ -n "${DOMAIN}" && "${DOMAIN}" != "${TLS_SERVER_NAME}" ]]; then
+    aliases+=("${DOMAIN}")
+  fi
+
+  if [[ -n "${DOMAIN}" && "www.${DOMAIN}" != "${TLS_SERVER_NAME}" ]]; then
+    aliases+=("www.${DOMAIN}")
+  fi
+
+  if (( ${#aliases[@]} > 0 )); then
+    printf 'ServerAlias %s\n' "${aliases[*]}"
+  fi
+}
 
-  local nginx_conf_tmp
-  local nginx_conf_target
+disable_nginx_if_present() {
+  if ! command -v systemctl >/dev/null 2>&1; then
+    return
+  fi
+
+  if systemctl list-unit-files nginx.service >/dev/null 2>&1; then
+    if systemctl is-active --quiet nginx; then
+      log "Stopping nginx so Apache can bind ports ${PROXY_HTTP_PORT}/${PROXY_HTTPS_PORT} ..."
+      run_root systemctl stop nginx
+    fi
+    if systemctl is-enabled --quiet nginx; then
+      run_root systemctl disable nginx || true
+    fi
+  fi
+}
 
-  nginx_conf_tmp="$(mktemp)"
-  nginx_conf_target="/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"
+write_apache_config() {
+  (( TLS_ACTIVE )) || return
 
-  cat > "${nginx_conf_tmp}" <<EOF_NGINX
-server {
-    listen ${PROXY_HTTP_PORT};
-    listen [::]:${PROXY_HTTP_PORT};
-    server_name ${TLS_SERVER_NAME};
-
-    location / {
-        return 301 https://\$host\$request_uri;
-    }
-}
-
-server {
-    listen ${PROXY_HTTPS_PORT} ssl http2;
-    listen [::]:${PROXY_HTTPS_PORT} ssl http2;
-    server_name ${TLS_SERVER_NAME};
-
-    ssl_certificate ${FULLCHAIN_PATH};
-    ssl_certificate_key ${PRIVKEY_PATH};
-    ssl_session_timeout 1d;
-    ssl_session_cache shared:SSL:10m;
-    ssl_protocols TLSv1.2 TLSv1.3;
-    ssl_prefer_server_ciphers off;
-
-    client_max_body_size 50m;
-
-    location / {
-        proxy_pass http://${APP_BIND_HOST}:${APP_HOST_PORT};
-        proxy_http_version 1.1;
-        proxy_set_header Host \$host;
-        proxy_set_header X-Real-IP \$remote_addr;
-        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
-        proxy_set_header X-Forwarded-Proto https;
-        proxy_set_header X-Forwarded-Host \$host;
-        proxy_set_header Upgrade \$http_upgrade;
-        proxy_set_header Connection \"upgrade\";
-    }
-}
-EOF_NGINX
-
-  run_root install -m 644 "${nginx_conf_tmp}" "${nginx_conf_target}"
-  run_root ln -sfn "${nginx_conf_target}" "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf"
-  run_root rm -f /etc/nginx/sites-enabled/default
-  run_root nginx -t
-  run_root systemctl enable --now nginx
-  run_root systemctl reload nginx
+  local apache_conf_tmp
+  local apache_conf_target
+  local server_alias_line
+
+  apache_conf_tmp="$(mktemp)"
+  apache_conf_target="/etc/apache2/sites-available/${APACHE_SITE_NAME}.conf"
+  server_alias_line="$(apache_server_aliases)"
+
+  cat > "${apache_conf_tmp}" <<EOF_APACHE
+<VirtualHost *:${PROXY_HTTP_PORT}>
+    ServerName ${TLS_SERVER_NAME}
+    ${server_alias_line}
+
+    RewriteEngine On
+    RewriteRule ^/(.*)$ https://%{HTTP_HOST}/\$1 [R=301,L]
+</VirtualHost>
+
+<VirtualHost *:${PROXY_HTTPS_PORT}>
+    ServerName ${TLS_SERVER_NAME}
+    ${server_alias_line}
+
+    SSLEngine on
+    SSLCertificateFile ${FULLCHAIN_PATH}
+    SSLCertificateKeyFile ${PRIVKEY_PATH}
+
+    ProxyPreserveHost On
+    ProxyRequests Off
+    SSLProxyEngine Off
+
+    RequestHeader set X-Forwarded-Proto "https"
+    RequestHeader set X-Forwarded-Port "${PROXY_HTTPS_PORT}"
+    RequestHeader set X-Forwarded-Host "%{Host}i"
+
+    ProxyPass / http://${APP_UPSTREAM_HOST}:${APP_HOST_PORT}/ connectiontimeout=5 timeout=60 keepalive=On
+    ProxyPassReverse / http://${APP_UPSTREAM_HOST}:${APP_HOST_PORT}/
+</VirtualHost>
+EOF_APACHE
+
+  disable_nginx_if_present
+  run_root a2enmod ssl proxy proxy_http headers rewrite
+  run_root a2dissite 000-default.conf >/dev/null 2>&1 || true
+  run_root a2dissite default-ssl.conf >/dev/null 2>&1 || true
+  run_root install -m 644 "${apache_conf_tmp}" "${apache_conf_target}"
+  run_root a2ensite "${APACHE_SITE_NAME}.conf"
+  run_root apache2ctl configtest
+  run_root systemctl enable --now apache2
+  run_root systemctl reload apache2
 
-  rm -f "${nginx_conf_tmp}"
+  rm -f "${apache_conf_tmp}"
 }
 
 create_superuser_if_requested() {
@@ -491,10 +519,10 @@
   log "Logs: docker logs -f ${CONTAINER_NAME}"
 
   if (( TLS_ACTIVE )); then
-    log "Nginx site: /etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"
+    log "Apache site: /etc/apache2/sites-available/${APACHE_SITE_NAME}.conf"
     log "Certificate chain: ${FULLCHAIN_PATH}"
     log "Private key: ${PRIVKEY_PATH}"
-    log "App is published internally at http://${APP_BIND_HOST}:${APP_HOST_PORT}"
+    log "App upstream target: http://${APP_UPSTREAM_HOST}:${APP_HOST_PORT}"
   fi
 }
 
@@ -516,7 +544,7 @@
   start_container
 
   if (( TLS_ACTIVE )); then
-    write_nginx_config
+    write_apache_config
   fi
 
   create_superuser_if_requested
>>>>>>> c40308404bdd33743bcf0021a82ca73f5434015e

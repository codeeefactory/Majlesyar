#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-majlesyar}"
IMAGE_NAME="${IMAGE_NAME:-${APP_NAME}:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-${APP_NAME}}"
BOT_CONTAINER_NAME="${BOT_CONTAINER_NAME:-${APP_NAME}-telegram-bot}"
HOST_PORT="${HOST_PORT:-127.0.0.1:8000}"
APP_PORT="${APP_PORT:-8000}"
DOMAIN="${DOMAIN:-majlesyar.com}"
REPO_URL="${REPO_URL:-https://github.com/codeeefactory/Majlesyar.git}"
REPO_REF="${REPO_REF:-master}"
WORKDIR="${WORKDIR:-/opt/majlesyar}"
DATA_DIR="${DATA_DIR:-/opt/majlesyar_data}"
BACKUP_DIR="${BACKUP_DIR:-/opt/majlesyar_backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"
LEGACY_MEDIA_DIR="${LEGACY_MEDIA_DIR:-/opt/majlesyar/.deploy/media}"
LEGACY_DB_PATH="${LEGACY_DB_PATH:-/opt/majlesyar/.deploy/db.sqlite3}"
APP_START_CMD="${APP_START_CMD:-python manage.py migrate --noinput && python manage.py sync_product_categories && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1200 --max-requests-jitter 100}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@majlesyar.com}"
BOT_POLL_TIMEOUT="${BOT_POLL_TIMEOUT:-5}"
BOT_SLEEP_SECONDS="${BOT_SLEEP_SECONDS:-5}"
DEPLOY_ROLE="${DEPLOY_ROLE:-origin}"
GEO_ASSET_DIR_REL="${GEO_ASSET_DIR_REL:-infra/geodns}"
GEO_RUNTIME_ROOT="${GEO_RUNTIME_ROOT:-/opt/majlesyar_geodns}"
TEXTFILE_DIR="${TEXTFILE_DIR:-/var/lib/prometheus/node-exporter}"
MONITORING_SOURCE_CIDR="${MONITORING_SOURCE_CIDR:-}"
SSH_DISABLE_PASSWORD_AUTH="${SSH_DISABLE_PASSWORD_AUTH:-0}"
ORIGIN_SERVER_NAMES="${ORIGIN_SERVER_NAMES:-${DOMAIN}}"
TLS_CERT_PATH="${TLS_CERT_PATH:-/etc/letsencrypt/live/${DOMAIN}/fullchain.pem}"
TLS_KEY_PATH="${TLS_KEY_PATH:-/etc/letsencrypt/live/${DOMAIN}/privkey.pem}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
CERTBOT_DOMAINS="${CERTBOT_DOMAINS:-}"
MAXMIND_ACCOUNT_ID="${MAXMIND_ACCOUNT_ID:-}"
MAXMIND_LICENSE_KEY="${MAXMIND_LICENSE_KEY:-}"
PDNS_API_KEY="${PDNS_API_KEY:-}"
DNS_PRIMARY="${DNS_PRIMARY:-0}"
SECONDARY_SSH_TARGET="${SECONDARY_SSH_TARGET:-}"
SECONDARY_ZONE_OUTPUT="${SECONDARY_ZONE_OUTPUT:-/etc/powerdns/geoip/majlesyar.com.yaml}"
SECONDARY_DNSSEC_KEYDIR="${SECONDARY_DNSSEC_KEYDIR:-/var/lib/powerdns/geoip-keys}"
PRIMARY_DNS_SSH_SOURCE="${PRIMARY_DNS_SSH_SOURCE:-}"
CONTROLLER_SSH_TARGET="${CONTROLLER_SSH_TARGET:-}"
CONTROLLER_STATE_DIR="${CONTROLLER_STATE_DIR:-/opt/majlesyar_geodns/probe-state}"
REGION="${REGION:-global}"
PROMETHEUS_ENABLE="${PROMETHEUS_ENABLE:-0}"

log() {
  printf '[startup][%s] %s\n' "${DEPLOY_ROLE}" "$*"
}

env_is_truthy() {
  local value="${1:-}"
  value="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
  [[ "${value}" == "1" || "${value}" == "true" || "${value}" == "yes" || "${value}" == "on" ]]
}

apt_install() {
  apt-get update -y
  apt-get install -y "$@"
}

ensure_base_packages() {
  apt_install git curl ca-certificates rsync jq python3 python3-yaml dnsutils ufw fail2ban openssl
}

ensure_cron() {
  apt_install cron sqlite3
  systemctl enable --now cron
}

ensure_nginx() {
  apt_install nginx
  mkdir -p /etc/nginx/snippets /var/www/certbot /var/www/majlesyar-maintenance
  systemctl enable --now nginx
}

ensure_prometheus_node_exporter() {
  apt_install prometheus-node-exporter
  mkdir -p "${TEXTFILE_DIR}"
  cat > /etc/default/prometheus-node-exporter <<EOF
ARGS="--collector.textfile.directory=${TEXTFILE_DIR}"
EOF
  systemctl enable --now prometheus-node-exporter
  systemctl restart prometheus-node-exporter
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
}

install_powerdns_repo() {
  . /etc/os-release
  apt_install gnupg
  curl -fsSL https://repo.powerdns.com/FD380FBB-pub.asc | gpg --dearmor > /usr/share/keyrings/pdns-archive-keyring.gpg
  cat > /etc/apt/sources.list.d/pdns.list <<EOF
deb [signed-by=/usr/share/keyrings/pdns-archive-keyring.gpg] http://repo.powerdns.com/debian ${VERSION_CODENAME}-auth-50 main
EOF
  cat > /etc/apt/preferences.d/pdns <<'EOF'
Package: pdns-*
Pin: origin repo.powerdns.com
Pin-Priority: 600
EOF
}

ensure_powerdns() {
  install_powerdns_repo
  apt_install pdns-server pdns-backend-geoip geoipupdate
}

ensure_prometheus_controller() {
  apt_install prometheus
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/monitoring/prometheus.yml" /etc/prometheus/prometheus.yml
  mkdir -p /etc/prometheus/alerts.d
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/monitoring/alerts.yml" /etc/prometheus/alerts.d/majlesyar-geodns-alerts.yml
  systemctl enable --now prometheus
  systemctl restart prometheus
}

configure_firewall() {
  local role="$1"
  ufw --force reset
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  case "${role}" in
    origin|maintenance)
      ufw allow 80/tcp
      ufw allow 443/tcp
      ;;
    dns)
      ufw allow 53/tcp
      ufw allow 53/udp
      ;;
    probe)
      :
      ;;
  esac
  if [[ -n "${MONITORING_SOURCE_CIDR}" ]]; then
    ufw allow from "${MONITORING_SOURCE_CIDR}" to any port 9100 proto tcp
  fi
  ufw --force enable
}

configure_fail2ban() {
  local role="$1"
  cat > /etc/fail2ban/jail.d/majlesyar.conf <<EOF
[sshd]
enabled = true
bantime = 1h
findtime = 10m
maxretry = 5
$(if [[ "${role}" == "origin" || "${role}" == "maintenance" ]]; then cat <<'NGINX'

[nginx-http-auth]
enabled = true

[nginx-botsearch]
enabled = true
NGINX
fi)
EOF
  systemctl enable --now fail2ban
  systemctl restart fail2ban
}

configure_ssh_hardening() {
  if ! env_is_truthy "${SSH_DISABLE_PASSWORD_AUTH}"; then
    return
  fi
  mkdir -p /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/60-majlesyar-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
  systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
}

copy_geo_assets() {
  mkdir -p /usr/local/lib/majlesyar /usr/local/share/majlesyar-geodns
  rsync -a "${WORKDIR}/${GEO_ASSET_DIR_REL}/scripts/" /usr/local/lib/majlesyar/
  chmod +x /usr/local/lib/majlesyar/*.py /usr/local/lib/majlesyar/*.sh
  rsync -a "${WORKDIR}/${GEO_ASSET_DIR_REL}/" /usr/local/share/majlesyar-geodns/
}

update_repo() {
  if [[ -d "${WORKDIR}/.git" ]]; then
    git -C "${WORKDIR}" remote set-url origin "${REPO_URL}"
    if [[ -n "$(git -C "${WORKDIR}" status --porcelain --untracked-files=no)" ]]; then
      log "existing repo has local changes; archiving it and cloning a fresh copy instead of overwriting"
    else
      git -C "${WORKDIR}" fetch --depth 1 origin "${REPO_REF}"
      git -C "${WORKDIR}" checkout -B "${REPO_REF}" "origin/${REPO_REF}"
      return
    fi
  fi

  if [[ -d "${WORKDIR}" ]]; then
    local ts legacy_archive_root
    ts="$(date +%F_%H%M%S)"
    legacy_archive_root="/opt/majlesyar_legacy"
    mkdir -p "${legacy_archive_root}"
    mv "${WORKDIR}" "${legacy_archive_root}/majlesyar_${ts}"
  fi

  git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" "${WORKDIR}"
}

env_file_has_key() {
  local key="$1"
  [[ -f "${DATA_DIR}/.env.production" ]] && grep -q "^${key}=" "${DATA_DIR}/.env.production"
}

ensure_env_var_default() {
  local key="$1"
  local value="$2"
  if ! env_file_has_key "${key}"; then
    printf '%s=%s\n' "${key}" "${value}" >> "${DATA_DIR}/.env.production"
  fi
}

env_file_get() {
  local key="$1"
  awk -F= -v key="${key}" '$1 == key { sub(/^[^=]*=/, "", $0); print $0; exit }' "${DATA_DIR}/.env.production"
}

create_predeploy_backup() {
  local ts work_dir
  ts="$(date +%F_%H%M%S)"
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' RETURN

  if [[ -f "${DATA_DIR}/db.sqlite3" ]]; then
    sqlite3 "${DATA_DIR}/db.sqlite3" ".backup '$work_dir/db.sqlite3'"
  fi
  if [[ -d "${DATA_DIR}/media" ]]; then
    rsync -a "${DATA_DIR}/media/" "${work_dir}/media/"
  fi
  if [[ -f "${DATA_DIR}/.env.production" ]]; then
    cp "${DATA_DIR}/.env.production" "${work_dir}/.env.production"
  fi

  tar -czf "${BACKUP_DIR}/predeploy_${ts}.tar.gz" -C "${work_dir}" .
}

prepare_origin_data() {
  mkdir -p "${DATA_DIR}/media" "${BACKUP_DIR}"

  if [[ -d "${LEGACY_MEDIA_DIR}" ]]; then
    rsync -a "${LEGACY_MEDIA_DIR}/" "${DATA_DIR}/media/"
  fi

  if [[ -f "${LEGACY_DB_PATH}" && ! -s "${DATA_DIR}/db.sqlite3" ]]; then
    sqlite3 "${LEGACY_DB_PATH}" ".backup '${DATA_DIR}/db.sqlite3'"
  fi

  touch "${DATA_DIR}/db.sqlite3"

  if [[ ! -f "${DATA_DIR}/.env.production" ]]; then
    cat > "${DATA_DIR}/.env.production" <<ENV
PORT=8000
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$(openssl rand -hex 48)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,${DOMAIN},www.${DOMAIN}
DJANGO_MEDIA_ROOT=/app/media
CORS_ALLOWED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
ENV
  fi

  ensure_env_var_default "TELEGRAM_BOT_ENABLED" "0"
  ensure_env_var_default "TELEGRAM_BOT_TOKEN" ""
  ensure_env_var_default "TELEGRAM_BOT_USE_WEBHOOK" "1"
  ensure_env_var_default "TELEGRAM_BOT_WEBHOOK_SECRET" ""
  ensure_env_var_default "TELEGRAM_BOT_WEBHOOK_PATH" "api/v1/telegram/webhook/"
  ensure_env_var_default "TELEGRAM_BOT_BASE_URL" "https://${DOMAIN}"
  ensure_env_var_default "TELEGRAM_BOT_ALLOWED_USER_IDS" ""
  ensure_env_var_default "TELEGRAM_BOT_ALLOWED_CHAT_IDS" ""
  ensure_env_var_default "TELEGRAM_BOT_ADMIN_ONLY" "1"
  ensure_env_var_default "TELEGRAM_BOT_NOTIFICATIONS_ENABLED" "0"
  ensure_env_var_default "TELEGRAM_BOT_CONFIRMATION_TTL_SECONDS" "600"
  ensure_env_var_default "TELEGRAM_BOT_RATE_LIMIT_PER_MINUTE" "30"
}

build_origin_image() {
  cd "${WORKDIR}"
  create_predeploy_backup
  docker build -t "${IMAGE_NAME}" .
}

local_healthcheck_url() {
  local host_spec="${HOST_PORT}"
  local bind_port bind_host
  bind_port="${host_spec##*:}"
  bind_host="127.0.0.1"
  if [[ "${host_spec}" == *:* ]]; then
    bind_host="${host_spec%:*}"
  fi
  if [[ -z "${bind_port}" || "${bind_port}" == "${host_spec}" && "${host_spec}" != *:* ]]; then
    bind_port="${host_spec}"
  fi
  if [[ -z "${bind_port}" ]]; then
    bind_port="${APP_PORT}"
  fi
  if [[ "${bind_host}" == "0.0.0.0" || "${bind_host}" == "::" || "${bind_host}" == "[::]" || -z "${bind_host}" ]]; then
    bind_host="127.0.0.1"
  fi
  printf 'http://%s:%s/api/v1/health/' "${bind_host}" "${bind_port}"
}

run_origin_container() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --env-file "${DATA_DIR}/.env.production" \
    -e PORT="${APP_PORT}" \
    -p "${HOST_PORT}:${APP_PORT}" \
    -v "${DATA_DIR}/db.sqlite3:/app/db.sqlite3" \
    -v "${DATA_DIR}/media:/app/media" \
    "${IMAGE_NAME}" \
    sh -c "${APP_START_CMD}"

  sleep 5
  docker logs --tail 50 "${CONTAINER_NAME}"
  curl --fail --silent --show-error --retry 12 --retry-delay 2 "$(local_healthcheck_url)" >/dev/null
}

ensure_admin_user() {
  docker exec \
    -e DJANGO_SUPERUSER_USERNAME="${ADMIN_USERNAME}" \
    -e DJANGO_SUPERUSER_PASSWORD="${ADMIN_PASSWORD}" \
    -e DJANGO_SUPERUSER_EMAIL="${ADMIN_EMAIL}" \
    "${CONTAINER_NAME}" \
    python manage.py shell -c "exec(\"\"\"from django.contrib.auth import get_user_model
User = get_user_model()
username = '${ADMIN_USERNAME}'
email = '${ADMIN_EMAIL}'
password = '${ADMIN_PASSWORD}'
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

configure_telegram_bot() {
  local bot_enabled bot_token use_webhook
  bot_enabled="$(env_file_get TELEGRAM_BOT_ENABLED)"
  bot_token="$(env_file_get TELEGRAM_BOT_TOKEN)"
  use_webhook="$(env_file_get TELEGRAM_BOT_USE_WEBHOOK)"

  docker rm -f "${BOT_CONTAINER_NAME}" >/dev/null 2>&1 || true

  if ! env_is_truthy "${bot_enabled}"; then
    log "telegram bot disabled"
    return
  fi
  if [[ -z "${bot_token}" ]]; then
    log "telegram bot enabled but TELEGRAM_BOT_TOKEN is empty"
    return
  fi
  if env_is_truthy "${use_webhook}"; then
    docker exec "${CONTAINER_NAME}" python manage.py configure_telegram_webhook
    log "telegram bot webhook configured"
    return
  fi

  docker exec "${CONTAINER_NAME}" python manage.py configure_telegram_webhook --delete >/dev/null 2>&1 || true
  docker run -d \
    --name "${BOT_CONTAINER_NAME}" \
    --restart unless-stopped \
    --env-file "${DATA_DIR}/.env.production" \
    -v "${DATA_DIR}/db.sqlite3:/app/db.sqlite3" \
    -v "${DATA_DIR}/media:/app/media" \
    "${IMAGE_NAME}" \
    sh -c "python manage.py migrate --noinput && python manage.py run_telegram_bot --poll-timeout ${BOT_POLL_TIMEOUT} --sleep-seconds ${BOT_SLEEP_SECONDS}"
}

install_backup_cron() {
  cat > /usr/local/bin/majlesyar-backup.sh <<SH
#!/usr/bin/env bash
set -Eeuo pipefail

DATA_DIR="${DATA_DIR}"
BACKUP_DIR="${BACKUP_DIR}"
RETENTION_DAYS="${RETENTION_DAYS}"

ts="\$(date +%F_%H%M%S)"
work_dir="\$(mktemp -d)"
trap 'rm -rf "\$work_dir"' EXIT

db_src="\$DATA_DIR/db.sqlite3"
db_bak="\$work_dir/db.sqlite3"
media_src="\$DATA_DIR/media"
env_src="\$DATA_DIR/.env.production"

if [[ -f "\$db_src" ]]; then
  sqlite3 "\$db_src" ".backup '\$db_bak'"
fi

archive="\$BACKUP_DIR/majlesyar_\$ts.tar.gz"
tar -czf "\$archive" -C "\$work_dir" db.sqlite3 2>/dev/null || true
if [[ -d "\$media_src" ]]; then
  tar -rzf "\$archive" -C "\$DATA_DIR" media
fi
if [[ -f "\$env_src" ]]; then
  tar -rzf "\$archive" -C "\$DATA_DIR" .env.production
fi

find "\$BACKUP_DIR" -type f -name "majlesyar_*.tar.gz" -mtime "+\$RETENTION_DAYS" -delete
SH
  chmod +x /usr/local/bin/majlesyar-backup.sh
  local cron_line
  cron_line="${CRON_SCHEDULE} /usr/local/bin/majlesyar-backup.sh >/var/log/majlesyar-backup.log 2>&1"
  (crontab -l 2>/dev/null | grep -v "majlesyar-backup.sh" || true; echo "${cron_line}") | crontab -
}

install_host_metrics_timer() {
  local role="$1"
  local nginx_url="http://127.0.0.1/api/v1/health/"
  local app_url="http://127.0.0.1:8000/api/v1/health/"
  if [[ "${role}" == "maintenance" ]]; then
    nginx_url="http://127.0.0.1/"
    app_url="http://127.0.0.1/"
  fi
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-host-metrics.service" /etc/systemd/system/
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-host-metrics.timer" /etc/systemd/system/
  cat > /etc/default/majlesyar-host-metrics <<EOF
ROLE=${role}
PROM_OUT=${TEXTFILE_DIR}/majlesyar_host.prom
CONTAINER_NAME=${CONTAINER_NAME}
NGINX_URL=${nginx_url}
APP_URL=${app_url}
MAXMIND_PATH=/var/lib/GeoIP/GeoLite2-Country.mmdb
EOF
  systemctl daemon-reload
  systemctl enable --now majlesyar-host-metrics.timer
}

write_origin_http_conf() {
  cat > /etc/nginx/sites-available/majlesyar-origin.conf <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${ORIGIN_SERVER_NAMES};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/majlesyar-proxy.conf;
    }
}

maybe_issue_certbot_cert() {
  local certbot_domains=()
  local certbot_args=()
  local certbot_domain

  if [[ -z "${CERTBOT_EMAIL}" || -z "${CERTBOT_DOMAINS}" ]]; then
    return
  fi

  read -r -a certbot_domains <<< "${CERTBOT_DOMAINS}"
  for certbot_domain in "${certbot_domains[@]}"; do
    certbot_args+=(-d "${certbot_domain}")
  done

  if [[ ${#certbot_args[@]} -eq 0 ]]; then
    log "CERTBOT_DOMAINS was provided but no domain names were parsed."
    return 1
  fi

  apt_install certbot python3-certbot-nginx
  certbot --nginx --non-interactive --agree-tos -m "${CERTBOT_EMAIL}" "${certbot_args[@]}"
}
EOF
}

write_origin_https_conf() {
  cat > /etc/nginx/sites-available/majlesyar-origin.conf <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${ORIGIN_SERVER_NAMES};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${ORIGIN_SERVER_NAMES};

    ssl_certificate ${TLS_CERT_PATH};
    ssl_certificate_key ${TLS_KEY_PATH};
    ssl_session_timeout 1d;
    ssl_session_cache shared:MajlesyarSSL:10m;
    ssl_protocols TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy same-origin always;

    client_max_body_size 32m;

    location /api/docs/ {
        include /etc/nginx/snippets/majlesyar-admin-allowlist.conf;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/majlesyar-proxy.conf;
    }

    location /majmanage/ {
        include /etc/nginx/snippets/majlesyar-admin-allowlist.conf;
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/majlesyar-proxy.conf;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/snippets/majlesyar-proxy.conf;
    }
}
EOF
}

configure_origin_nginx() {
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/nginx/proxy.conf" /etc/nginx/snippets/majlesyar-proxy.conf
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/nginx/admin-allowlist.conf.example" /etc/nginx/snippets/majlesyar-admin-allowlist.conf

  if [[ -n "${CERTBOT_EMAIL}" && -n "${CERTBOT_DOMAINS}" ]]; then
    write_origin_http_conf
    ln -sf /etc/nginx/sites-available/majlesyar-origin.conf /etc/nginx/sites-enabled/majlesyar-origin.conf
    rm -f /etc/nginx/sites-enabled/default
    systemctl restart nginx
    maybe_issue_certbot_cert
  fi

  if [[ -f "${TLS_CERT_PATH}" && -f "${TLS_KEY_PATH}" ]]; then
    write_origin_https_conf
  else
    write_origin_http_conf
    log "TLS certs not present yet; left origin on HTTP bootstrap config."
  fi

  ln -sf /etc/nginx/sites-available/majlesyar-origin.conf /etc/nginx/sites-enabled/majlesyar-origin.conf
  rm -f /etc/nginx/sites-enabled/default
  systemctl restart nginx
}

write_maintenance_conf() {
  local conf="/etc/nginx/sites-available/majlesyar-maintenance.conf"
  if [[ -f "${TLS_CERT_PATH}" && -f "${TLS_KEY_PATH}" ]]; then
    cat > "${conf}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${ORIGIN_SERVER_NAMES};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${ORIGIN_SERVER_NAMES};

    ssl_certificate ${TLS_CERT_PATH};
    ssl_certificate_key ${TLS_KEY_PATH};

    root /var/www/majlesyar-maintenance;
    index index.html;

    add_header Cache-Control "no-store" always;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
  else
    cat > "${conf}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${ORIGIN_SERVER_NAMES};
    root /var/www/majlesyar-maintenance;
    index index.html;
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
    log "TLS certs not present yet; left maintenance host on HTTP bootstrap config."
  fi
  ln -sf "${conf}" /etc/nginx/sites-enabled/majlesyar-maintenance.conf
  rm -f /etc/nginx/sites-enabled/default
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/maintenance/index.html" /var/www/majlesyar-maintenance/index.html
  systemctl restart nginx
}

configure_geoip_credentials() {
  if [[ -z "${MAXMIND_ACCOUNT_ID}" || -z "${MAXMIND_LICENSE_KEY}" ]]; then
    log "MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY are required for dns role."
    exit 1
  fi
  cat > /etc/GeoIP.conf <<EOF
AccountID ${MAXMIND_ACCOUNT_ID}
LicenseKey ${MAXMIND_LICENSE_KEY}
EditionIDs GeoLite2-Country
DatabaseDirectory /var/lib/GeoIP
EOF
  chmod 0600 /etc/GeoIP.conf
  mkdir -p /var/lib/GeoIP
  geoipupdate
}

configure_powerdns() {
  mkdir -p /etc/powerdns/pdns.d /etc/powerdns/geoip "${GEO_RUNTIME_ROOT}/config" "${GEO_RUNTIME_ROOT}/state" "${GEO_RUNTIME_ROOT}/probe-state" /var/lib/powerdns/geoip-keys
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/pdns/pdns.conf" /etc/powerdns/pdns.conf
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/pdns/pdns.d/geoip.conf" /etc/powerdns/pdns.d/geoip.conf
  if [[ -z "${PDNS_API_KEY}" ]]; then
    PDNS_API_KEY="$(openssl rand -hex 24)"
  fi
  sed -i "s/api-key=replace-me/api-key=${PDNS_API_KEY}/" /etc/powerdns/pdns.conf
  if [[ ! -f "${GEO_RUNTIME_ROOT}/config/site.yaml" ]]; then
    cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/config/site.yaml" "${GEO_RUNTIME_ROOT}/config/site.yaml"
  fi
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/config/failover-state.example.json" "${GEO_RUNTIME_ROOT}/state/failover-state.seed.json"
  python3 /usr/local/lib/majlesyar/render_geo_zone.py \
    --site-config "${GEO_RUNTIME_ROOT}/config/site.yaml" \
    --state "${GEO_RUNTIME_ROOT}/state/failover-state.seed.json" \
    --output /etc/powerdns/geoip/majlesyar.com.yaml
  chmod 0700 /var/lib/powerdns/geoip-keys
  chown -R pdns:pdns /etc/powerdns /var/lib/powerdns /var/lib/GeoIP
  systemctl enable --now pdns
  if env_is_truthy "${DNS_PRIMARY}" && [[ -z "$(find /var/lib/powerdns/geoip-keys -type f 2>/dev/null)" ]]; then
    pdnsutil zone secure "${DOMAIN}" || true
  fi
  if ! env_is_truthy "${DNS_PRIMARY}" && [[ -n "${PRIMARY_DNS_SSH_SOURCE}" ]]; then
    rsync -az "${PRIMARY_DNS_SSH_SOURCE}:/etc/powerdns/geoip/majlesyar.com.yaml" /etc/powerdns/geoip/majlesyar.com.yaml
    rsync -az "${PRIMARY_DNS_SSH_SOURCE}:/var/lib/powerdns/geoip-keys/" /var/lib/powerdns/geoip-keys/
    chown -R pdns:pdns /etc/powerdns /var/lib/powerdns
    systemctl restart pdns
  fi
}

install_geodns_timer() {
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-geodns.service" /etc/systemd/system/
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-geodns.timer" /etc/systemd/system/
  cat > /etc/default/majlesyar-geodns <<EOF
SITE_CONFIG=${GEO_RUNTIME_ROOT}/config/site.yaml
IRAN_PROBE_STATE=${GEO_RUNTIME_ROOT}/probe-state/iran.json
GLOBAL_PROBE_STATE=${GEO_RUNTIME_ROOT}/probe-state/global.json
STATE_OUTPUT=${GEO_RUNTIME_ROOT}/state/failover-state.json
HISTORY_PATH=${GEO_RUNTIME_ROOT}/state/history.json
MANUAL_OVERRIDE_PATH=${GEO_RUNTIME_ROOT}/state/manual-override.json
ZONE_OUTPUT=/etc/powerdns/geoip/majlesyar.com.yaml
SECONDARY_SSH_TARGET=${SECONDARY_SSH_TARGET}
SECONDARY_ZONE_OUTPUT=${SECONDARY_ZONE_OUTPUT}
DNSSEC_KEYDIR=/var/lib/powerdns/geoip-keys
SECONDARY_DNSSEC_KEYDIR=${SECONDARY_DNSSEC_KEYDIR}
EOF
  systemctl daemon-reload
  systemctl enable --now majlesyar-geodns.timer
}

install_probe_timer() {
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-probe.service" /etc/systemd/system/
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-probe.timer" /etc/systemd/system/
  mkdir -p "${GEO_RUNTIME_ROOT}/config" "${GEO_RUNTIME_ROOT}/state"
  if [[ ! -f "${GEO_RUNTIME_ROOT}/config/site.yaml" ]]; then
    cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/config/site.yaml" "${GEO_RUNTIME_ROOT}/config/site.yaml"
  fi
  cat > /etc/default/majlesyar-geo-probe <<EOF
SITE_CONFIG=${GEO_RUNTIME_ROOT}/config/site.yaml
REGION=${REGION}
JSON_OUTPUT=${GEO_RUNTIME_ROOT}/state/${REGION}.json
PROM_OUTPUT=${TEXTFILE_DIR}/majlesyar_probe_${REGION}.prom
CONTROLLER_SSH_TARGET=${CONTROLLER_SSH_TARGET}
CONTROLLER_STATE_DIR=${CONTROLLER_STATE_DIR}
EOF
  systemctl daemon-reload
  systemctl enable --now majlesyar-probe.timer
}

install_geoip_timer() {
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-geoipupdate.service" /etc/systemd/system/
  cp "${WORKDIR}/${GEO_ASSET_DIR_REL}/systemd/majlesyar-geoipupdate.timer" /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now majlesyar-geoipupdate.timer
}

install_origin_role() {
  ensure_base_packages
  ensure_cron
  ensure_nginx
  ensure_prometheus_node_exporter
  ensure_docker
  configure_firewall origin
  configure_fail2ban origin
  configure_ssh_hardening
  prepare_origin_data
  update_repo
  copy_geo_assets
  build_origin_image
  run_origin_container
  ensure_admin_user
  configure_telegram_bot
  configure_origin_nginx
  install_backup_cron
  install_host_metrics_timer origin
}

install_maintenance_role() {
  ensure_base_packages
  ensure_nginx
  ensure_prometheus_node_exporter
  configure_firewall maintenance
  configure_fail2ban maintenance
  configure_ssh_hardening
  update_repo
  copy_geo_assets
  write_maintenance_conf
  if [[ -n "${CERTBOT_EMAIL}" && -n "${CERTBOT_DOMAINS}" ]]; then
    maybe_issue_certbot_cert
    write_maintenance_conf
  fi
  install_host_metrics_timer maintenance
}

install_dns_role() {
  ensure_base_packages
  ensure_prometheus_node_exporter
  configure_firewall dns
  configure_fail2ban dns
  configure_ssh_hardening
  update_repo
  copy_geo_assets
  ensure_powerdns
  configure_geoip_credentials
  configure_powerdns
  install_geoip_timer
  install_host_metrics_timer dns
  if env_is_truthy "${DNS_PRIMARY}" && env_is_truthy "${PROMETHEUS_ENABLE}"; then
    ensure_prometheus_controller
  fi
  if env_is_truthy "${DNS_PRIMARY}"; then
    install_geodns_timer
  fi
}

install_probe_role() {
  ensure_base_packages
  ensure_prometheus_node_exporter
  configure_firewall probe
  configure_fail2ban probe
  configure_ssh_hardening
  update_repo
  copy_geo_assets
  install_probe_timer
}

main() {
  case "${DEPLOY_ROLE}" in
    origin)
      install_origin_role
      ;;
    maintenance)
      install_maintenance_role
      ;;
    dns)
      install_dns_role
      ;;
    probe)
      install_probe_role
      ;;
    *)
      log "Unsupported DEPLOY_ROLE=${DEPLOY_ROLE}"
      exit 1
      ;;
  esac

  log "Completed startup role ${DEPLOY_ROLE}"
}

main "$@"

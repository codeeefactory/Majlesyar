#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="majlesyar"
IMAGE_NAME="${APP_NAME}:latest"
CONTAINER_NAME="${APP_NAME}"
BOT_CONTAINER_NAME="${APP_NAME}-telegram-bot"
HOST_PORT="127.0.0.1:8000"
APP_PORT="8000"
DOMAIN="majlesyar.com"
REPO_URL="https://github.com/codeeefactory/Majlesyar.git"
REPO_REF="master"
WORKDIR="/opt/majlesyar"
DATA_DIR="/opt/majlesyar_data"
BACKUP_DIR="/opt/majlesyar_backups"
RETENTION_DAYS="7"
CRON_SCHEDULE="0 2 * * *"
LEGACY_MEDIA_DIR="/opt/majlesyar/.deploy/media"
LEGACY_DB_PATH="/opt/majlesyar/.deploy/db.sqlite3"
APP_START_CMD='python manage.py migrate --noinput && python manage.py sync_product_categories && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1200 --max-requests-jitter 100'
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin"
ADMIN_EMAIL="admin@majlesyar.com"
BOT_POLL_TIMEOUT="5"
BOT_SLEEP_SECONDS="5"

apt-get update -y && apt-get install -y git curl ca-certificates cron sqlite3 rsync nginx

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

systemctl enable --now cron

mkdir -p "$DATA_DIR/media"
mkdir -p "$BACKUP_DIR"

env_file_has_key() {
  local key="$1"
  grep -q "^${key}=" "$DATA_DIR/.env.production"
}

ensure_env_var_default() {
  local key="$1"
  local value="$2"
  if ! env_file_has_key "$key"; then
    printf '%s=%s\n' "$key" "$value" >> "$DATA_DIR/.env.production"
  fi
}

env_file_get() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, "", $0); print $0; exit }' "$DATA_DIR/.env.production"
}

env_is_truthy() {
  local value="${1:-}"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  [[ "$value" == "1" || "$value" == "true" || "$value" == "yes" || "$value" == "on" ]]
}

update_repo() {
  if [[ -d "$WORKDIR/.git" ]]; then
    git -C "$WORKDIR" remote set-url origin "$REPO_URL"
    git -C "$WORKDIR" fetch --depth 1 origin "$REPO_REF"
    git -C "$WORKDIR" checkout "$REPO_REF"
    git -C "$WORKDIR" reset --hard "origin/$REPO_REF"
    return
  fi

  if [[ -d "$WORKDIR" ]]; then
    ts="$(date +%F_%H%M%S)"
    LEGACY_ARCHIVE_ROOT="/opt/majlesyar_legacy"
    mkdir -p "$LEGACY_ARCHIVE_ROOT"
    mv "$WORKDIR" "$LEGACY_ARCHIVE_ROOT/majlesyar_$ts"
  fi

  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$WORKDIR"
}

create_predeploy_backup() {
  ts="$(date +%F_%H%M%S)"
  work_dir="$(mktemp -d)"
  trap 'rm -rf "$work_dir"' RETURN

  if [[ -f "$DATA_DIR/db.sqlite3" ]]; then
    sqlite3 "$DATA_DIR/db.sqlite3" ".backup '$work_dir/db.sqlite3'"
  fi
  if [[ -d "$DATA_DIR/media" ]]; then
    rsync -a "$DATA_DIR/media"/ "$work_dir/media"/
  fi
  if [[ -f "$DATA_DIR/.env.production" ]]; then
    cp "$DATA_DIR/.env.production" "$work_dir/.env.production"
  fi

  tar -czf "$BACKUP_DIR/predeploy_$ts.tar.gz" -C "$work_dir" .
}

# Migrate legacy media (stored inside WORKDIR) into persistent data dir before archive
if [[ -d "$LEGACY_MEDIA_DIR" ]]; then
  rsync -a "$LEGACY_MEDIA_DIR"/ "$DATA_DIR/media"/
fi

ensure_env_var_default "TELEGRAM_BOT_ENABLED" "0"
ensure_env_var_default "TELEGRAM_BOT_TOKEN" ""
ensure_env_var_default "TELEGRAM_BOT_USE_WEBHOOK" "1"
ensure_env_var_default "TELEGRAM_BOT_WEBHOOK_SECRET" ""
ensure_env_var_default "TELEGRAM_BOT_WEBHOOK_PATH" "api/v1/telegram/webhook/"
ensure_env_var_default "TELEGRAM_BOT_BASE_URL" "https://$DOMAIN"
ensure_env_var_default "TELEGRAM_BOT_ALLOWED_USER_IDS" ""
ensure_env_var_default "TELEGRAM_BOT_ALLOWED_CHAT_IDS" ""
ensure_env_var_default "TELEGRAM_BOT_ADMIN_ONLY" "1"
ensure_env_var_default "TELEGRAM_BOT_NOTIFICATIONS_ENABLED" "0"
ensure_env_var_default "TELEGRAM_BOT_CONFIRMATION_TTL_SECONDS" "600"
ensure_env_var_default "TELEGRAM_BOT_RATE_LIMIT_PER_MINUTE" "30"

# Migrate legacy db only if current db is missing or empty
if [[ -f "$LEGACY_DB_PATH" ]]; then
  if [[ ! -s "$DATA_DIR/db.sqlite3" ]]; then
    sqlite3 "$LEGACY_DB_PATH" ".backup '$DATA_DIR/db.sqlite3'"
  fi
fi

# Ensure db exists even if no legacy db was found
touch "$DATA_DIR/db.sqlite3"

update_repo

# Keep existing env to preserve secrets; create only if missing
if [[ ! -f "$DATA_DIR/.env.production" ]]; then
  cat > "$DATA_DIR/.env.production" <<ENV
PORT=8000
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$(openssl rand -hex 48)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN,www.$DOMAIN
DJANGO_MEDIA_ROOT=/app/media
CORS_ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
ENV
fi

cd "$WORKDIR"

create_predeploy_backup

docker build -t "$IMAGE_NAME" .

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --env-file "$DATA_DIR/.env.production" \
  -p 127.0.0.1:8000:8000 \
  -v "$DATA_DIR/db.sqlite3:/app/db.sqlite3" \
  -v "$DATA_DIR/media:/app/media" \
  "$IMAGE_NAME" \
  sh -c "$APP_START_CMD"

sleep 5
docker logs --tail 50 "$CONTAINER_NAME"

curl --fail --silent --show-error --retry 12 --retry-delay 2 http://127.0.0.1:8000 >/dev/null

if command -v systemctl >/dev/null 2>&1; then
  systemctl enable --now nginx
  systemctl restart nginx
fi

docker exec \
  -e DJANGO_SUPERUSER_USERNAME="$ADMIN_USERNAME" \
  -e DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASSWORD" \
  -e DJANGO_SUPERUSER_EMAIL="$ADMIN_EMAIL" \
  "$CONTAINER_NAME" \
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

configure_telegram_bot() {
  local bot_enabled
  local bot_token
  local use_webhook

  bot_enabled="$(env_file_get TELEGRAM_BOT_ENABLED)"
  bot_token="$(env_file_get TELEGRAM_BOT_TOKEN)"
  use_webhook="$(env_file_get TELEGRAM_BOT_USE_WEBHOOK)"

  docker rm -f "$BOT_CONTAINER_NAME" >/dev/null 2>&1 || true

  if ! env_is_truthy "$bot_enabled"; then
    echo "telegram bot disabled"
    return
  fi

  if [[ -z "${bot_token}" ]]; then
    echo "telegram bot enabled but TELEGRAM_BOT_TOKEN is empty"
    return
  fi

  if env_is_truthy "$use_webhook"; then
    docker exec "$CONTAINER_NAME" python manage.py configure_telegram_webhook
    echo "telegram bot webhook configured"
    return
  fi

  docker exec "$CONTAINER_NAME" python manage.py configure_telegram_webhook --delete >/dev/null 2>&1 || true

  docker run -d \
    --name "$BOT_CONTAINER_NAME" \
    --restart unless-stopped \
    --env-file "$DATA_DIR/.env.production" \
    -v "$DATA_DIR/db.sqlite3:/app/db.sqlite3" \
    -v "$DATA_DIR/media:/app/media" \
    "$IMAGE_NAME" \
    sh -c "python manage.py migrate --noinput && python manage.py run_telegram_bot --poll-timeout ${BOT_POLL_TIMEOUT} --sleep-seconds ${BOT_SLEEP_SECONDS}"

  sleep 3
  docker logs --tail 50 "$BOT_CONTAINER_NAME"
  echo "telegram bot polling worker started"
}

configure_telegram_bot

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

# Install/refresh cron schedule
cron_line="${CRON_SCHEDULE} /usr/local/bin/majlesyar-backup.sh >/var/log/majlesyar-backup.log 2>&1"
(crontab -l 2>/dev/null | grep -v "majlesyar-backup.sh" || true; echo "$cron_line") | crontab -

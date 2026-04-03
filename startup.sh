#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="majlesyar"
IMAGE_NAME="${APP_NAME}:latest"
CONTAINER_NAME="${APP_NAME}"
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

apt-get update -y && apt-get install -y git curl ca-certificates cron sqlite3 rsync

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

systemctl enable --now cron

mkdir -p "$DATA_DIR/media"
mkdir -p "$BACKUP_DIR"

# Migrate legacy media (stored inside WORKDIR) into persistent data dir before wipe
if [[ -d "$LEGACY_MEDIA_DIR" ]]; then
  rsync -a "$LEGACY_MEDIA_DIR"/ "$DATA_DIR/media"/
fi

# Migrate legacy db (stored inside WORKDIR) into persistent data dir before wipe
if [[ -f "$LEGACY_DB_PATH" ]]; then
  sqlite3 "$LEGACY_DB_PATH" ".backup '$DATA_DIR/db.sqlite3'"
fi

# Ensure db exists even if no legacy db was found
touch "$DATA_DIR/db.sqlite3"

# Archive existing deploy instead of wiping (keep legacy paths)
if [[ -d "$WORKDIR" ]]; then
  ts="$(date +%F_%H%M%S)"
  LEGACY_ARCHIVE_ROOT="/opt/majlesyar_legacy"
  mkdir -p "$LEGACY_ARCHIVE_ROOT"
  mv "$WORKDIR" "$LEGACY_ARCHIVE_ROOT/majlesyar_$ts"
fi
git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$WORKDIR"

cat > "$DATA_DIR/.env.production" <<ENV
PORT=8000
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$(openssl rand -hex 48)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN,www.$DOMAIN
DJANGO_MEDIA_ROOT=/app/media
CORS_ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
ENV

cd "$WORKDIR"

docker build -t "$IMAGE_NAME" .

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --env-file "$DATA_DIR/.env.production" \
  -p 127.0.0.1:8000:8000 \
  -v "$DATA_DIR/db.sqlite3:/app/db.sqlite3" \
  -v "$DATA_DIR/media:/app/media" \
  "$IMAGE_NAME"

sleep 5
docker logs --tail 50 "$CONTAINER_NAME"

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

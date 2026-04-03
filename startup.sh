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

apt-get update -y && apt-get install -y git curl ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

mkdir -p "$DATA_DIR/media"
touch "$DATA_DIR/db.sqlite3"

rm -rf "$WORKDIR"
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

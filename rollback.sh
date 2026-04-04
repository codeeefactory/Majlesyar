#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="majlesyar"
IMAGE_NAME="${APP_NAME}:latest"
CONTAINER_NAME="${APP_NAME}"
HOST_PORT="127.0.0.1:8000"
APP_PORT="8000"
WORKDIR="/opt/majlesyar"
DATA_DIR="/opt/majlesyar_data"
BACKUP_DIR="/opt/majlesyar_backups"
LEGACY_ARCHIVE_ROOT="/opt/majlesyar_legacy"
APP_START_CMD='python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1200 --max-requests-jitter 100'

apt-get update -y && apt-get install -y git curl ca-certificates sqlite3 rsync tar

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

mkdir -p "$DATA_DIR/media"
mkdir -p "$BACKUP_DIR"

pick_backup() {
  if [[ $# -gt 0 && -n "${1:-}" ]]; then
    printf '%s\n' "$1"
    return
  fi

  local backup_path
  backup_path="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'predeploy_*.tar.gz' | sort | tail -n 1)"
  if [[ -z "$backup_path" ]]; then
    echo "No predeploy backup found in $BACKUP_DIR" >&2
    exit 1
  fi

  printf '%s\n' "$backup_path"
}

restore_backup() {
  local backup_path="$1"
  local restore_dir
  restore_dir="$(mktemp -d)"
  trap 'rm -rf "$restore_dir"' RETURN

  tar -xzf "$backup_path" -C "$restore_dir"

  if [[ -f "$restore_dir/db.sqlite3" ]]; then
    sqlite3 "$restore_dir/db.sqlite3" ".backup '$DATA_DIR/db.sqlite3'"
  fi
  if [[ -d "$restore_dir/media" ]]; then
    rm -rf "$DATA_DIR/media"
    mkdir -p "$DATA_DIR/media"
    rsync -a "$restore_dir/media"/ "$DATA_DIR/media"/
  fi
  if [[ -f "$restore_dir/.env.production" ]]; then
    cp "$restore_dir/.env.production" "$DATA_DIR/.env.production"
  fi
}

restore_code() {
  if [[ -d "$WORKDIR/.git" ]] && git -C "$WORKDIR" rev-parse --verify ORIG_HEAD >/dev/null 2>&1; then
    git -C "$WORKDIR" reset --hard ORIG_HEAD
    return
  fi

  local legacy_dir
  legacy_dir="$(find "$LEGACY_ARCHIVE_ROOT" -maxdepth 1 -mindepth 1 -type d -name 'majlesyar_*' | sort | tail -n 1)"
  if [[ -n "$legacy_dir" ]]; then
    rm -rf "$WORKDIR"
    cp -a "$legacy_dir" "$WORKDIR"
    return
  fi

  echo "No previous app revision found to restore. Data rollback will still proceed." >&2
}

start_container() {
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
    "$IMAGE_NAME" \
    sh -c "$APP_START_CMD"
}

main() {
  local backup_path
  backup_path="$(pick_backup "${1:-}")"

  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  restore_code
  restore_backup "$backup_path"
  start_container

  sleep 5
  docker logs --tail 50 "$CONTAINER_NAME"
  printf 'Rollback completed using backup: %s\n' "$backup_path"
}

main "$@"

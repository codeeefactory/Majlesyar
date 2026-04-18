FROM node:20-alpine AS frontend-build

WORKDIR /workspace
COPY . .

RUN set -eux; \
    APP_DIR="."; \
    if [ ! -f package.json ]; then \
      APP_DIR=""; \
      for cand in */package.json; do \
        [ -e "$cand" ] || continue; \
        dir="$(dirname "$cand")"; \
        if [ -f "$dir/backend/requirements.txt" ]; then APP_DIR="$dir"; break; fi; \
      done; \
      [ -n "$APP_DIR" ] || { echo "No app root found (expected package.json + backend/requirements.txt)."; ls -la; exit 1; }; \
    fi; \
    cd "${APP_DIR}"; \
    npm ci; \
    npx vite build --base=/static/; \
    cp -a dist /frontend_dist


FROM python:3.12-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=120 \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=*

WORKDIR /workspace
COPY . .

RUN set -eux; \
    APP_DIR="."; \
    if [ ! -f backend/requirements.txt ]; then \
      APP_DIR=""; \
      for cand in */backend/requirements.txt; do \
        [ -e "$cand" ] || continue; \
        dir="$(dirname "$(dirname "$cand")")"; \
        if [ -f "$dir/package.json" ]; then APP_DIR="$dir"; break; fi; \
      done; \
      [ -n "$APP_DIR" ] || { echo "No backend root found (expected backend/requirements.txt)."; ls -la; exit 1; }; \
    fi; \
    python -m pip install -r "${APP_DIR}/backend/requirements.txt"; \
    mkdir -p /app; \
    cp -a "${APP_DIR}/backend/." /app/

COPY --from=frontend-build /frontend_dist /app/frontend_dist

WORKDIR /app
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_initial_data && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1200 --max-requests-jitter 100"]

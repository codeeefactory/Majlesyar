FROM node:20-alpine AS frontend-build

WORKDIR /frontend

COPY package*.json ./
RUN npm ci

COPY . ./
RUN npm run build -- --base=/static/


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

WORKDIR /app

COPY backend/requirements.txt ./
RUN python -m pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /frontend/dist /app/frontend_dist
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_initial_data && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --worker-class gthread --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1200 --max-requests-jitter 100"]

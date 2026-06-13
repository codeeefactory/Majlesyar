# Majlesyar

Full-stack project with:

- Frontend: Vite + React + TypeScript
- Backend: Django + DRF + Unfold admin + JWT auth

## Repository Layout

- Frontend app: `./` (root)
- Backend app: `./backend`
- Analysis docs:
  - `docs/PROJECT_ANALYSIS.md`
  - `docs/API_CONTRACT.md`

## Frontend Run

```powershell
npm install
copy .env.example .env
npm run dev
```

Frontend dev URL: `http://localhost:8080`

`VITE_API_BASE_URL` is optional. If not set, frontend calls same-origin `/api` (recommended for production and proxied dev).

## Backend Run (SQLite default)

```powershell
py -m venv backend/.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\backend\.venv\Scripts\python manage.py migrate
..\backend\.venv\Scripts\python manage.py seed_initial_data
..\backend\.venv\Scripts\python manage.py createsuperuser
..\backend\.venv\Scripts\python manage.py runserver
```

Backend URL: `http://localhost:8000`

## Seed Data

Seed source: `backend/seed/initial_data.json`

Run:

```powershell
cd backend
..\backend\.venv\Scripts\python manage.py seed_initial_data
```

## Admin + API

- Django admin (Unfold): `http://localhost:8000/admin/`
- Swagger docs: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- API base: `http://localhost:8000/api/v1/`

## Optional Docker Compose

Start backend with SQLite:

```powershell
docker compose up --build
```

Start backend + Postgres:

```powershell
$env:USE_POSTGRES="1"
docker compose --profile postgres up --build
```

## Production Docker Server Deploy

Use this when the whole project should run on a Docker server. It builds the React frontend, bundles it into Django, and starts Gunicorn.

### Dockerfile-only provider

Use this when your new server only accepts a `Dockerfile` and environment variables.

Set these env vars in the server panel:

```text
PORT=8000
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=change-this-to-a-long-random-secret
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com,SERVER_IP
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
USE_POSTGRES=0
SQLITE_DB_PATH=/data/db.sqlite3
DJANGO_MEDIA_ROOT=/data/media
```

Mount persistent storage to `/data` if the server supports volumes. Without that, SQLite database and uploaded media can be lost when the container is rebuilt.

Manual Dockerfile deploy:

```bash
cd Majlesyar
cp .env.dockerfile.example .env.dockerfile
# edit secrets/domains
docker build -t majlesyar:latest .
docker run -d --name majlesyar --restart unless-stopped --env-file .env.dockerfile -p 80:8000 -v majlesyar_data:/data majlesyar:latest
```

If the server provides Postgres, set `USE_POSTGRES=1` and fill `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

### Docker Compose server

```bash
cd Majlesyar
cp .env.production.example .env.production
# edit .env.production: DJANGO_SECRET_KEY, hosts, origins, POSTGRES_PASSWORD
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Or use the helper:

```bash
cd Majlesyar
bash scripts/deploy-docker-server.sh
```

Useful commands:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f app
docker compose --env-file .env.production -f docker-compose.prod.yml exec app python manage.py createsuperuser
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

## Fresh Debian Auto-Startup (Provider Startup Script)

You can use `Majlesyar/startup_linux.sh` directly as a server "startup script" on a fresh Debian VPS.

What it now does automatically:

1. Rewrites APT repos to Iranian mirror (default enabled via `APT_USE_IRAN_MIRROR=1`).
2. Installs Docker if missing.
3. Clones project source if Dockerfile/backend are not already present.
4. Builds image and starts container.

Recommended provider env vars:

```text
REPO_URL=https://github.com/codeeefactory/Majlesyar.git
REPO_REF=master
PROJECT_SUBDIR=Majlesyar
HOST_PORT=80
APP_PORT=8000
DOMAIN=your-domain.com
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-strong-password
```

Notes:

- If your provider has no env-var UI, edit the top of `startup_linux.sh` defaults before uploading.
- If you do not set `DOMAIN`, the script auto-uses server IP for `DJANGO_ALLOWED_HOSTS`.
- Startup logs can be checked with `docker logs -f majlesyar` after server is up.

## Smoke Checklist

1. Products page loads from backend (`/shop`).
2. Checkout creates order and redirects to `/order/{public_id}`.
3. Track order works via `/track`.
4. Admin login (`/admin/login`) returns JWT and admin orders load.
5. Django admin uses Unfold styling.

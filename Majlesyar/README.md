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

## Smoke Checklist

1. Products page loads from backend (`/shop`).
2. Checkout creates order and redirects to `/order/{public_id}`.
3. Track order works via `/track`.
4. Admin login (`/admin/login`) returns JWT and admin orders load.
5. Django admin uses Unfold styling.

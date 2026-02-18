# Backend (Django + DRF)

This backend powers catalog data, site settings, checkout/order creation, order tracking, and admin order operations.

## Stack

- Django
- Django REST Framework
- django-unfold (admin theme)
- django-cors-headers
- djangorestframework-simplejwt
- drf-spectacular (OpenAPI + Swagger)
- SQLite by default (optional Postgres)

## Quick Start (Windows)

From repository root:

```powershell
py -m venv backend/.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\backend\.venv\Scripts\python manage.py migrate
..\backend\.venv\Scripts\python manage.py seed_initial_data
..\backend\.venv\Scripts\python manage.py createsuperuser
..\backend\.venv\Scripts\python manage.py runserver
```

Server: `http://localhost:8000`

## Key URLs

- Admin: `http://localhost:8000/admin/`
- Swagger: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- API base: `http://localhost:8000/api/v1/`

## Seed Data

Initial data lives in:

- `backend/seed/initial_data.json`

Seed command:

```powershell
cd backend
..\backend\.venv\Scripts\python manage.py seed_initial_data
```

## Optional Postgres via Docker Compose

From repository root:

```powershell
docker compose --profile postgres up --build
```

If you want backend to use Postgres in Compose, set:

```powershell
$env:USE_POSTGRES="1"
docker compose --profile postgres up --build
```

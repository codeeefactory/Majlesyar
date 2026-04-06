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

## Product Images

- Product image upload is supported in:
  - `POST /api/v1/admin/products/`
  - `PATCH /api/v1/admin/products/{id}/`
- Use `multipart/form-data` and send the file in `image_file`.
- Validation:
  - Must be a valid image
  - Max size: 5MB
- Files are served under `/media/...` (toggle with `SERVE_MEDIA=1|0`).

## Local Product Recognition

The backend now supports internal-only product photo analysis for these labels:

- `halva` => `حلوا`
- `date` => `خرما`
- `orange` => `پرتقال`
- `tangerine` => `نارنگی`
- `banana` => `موز`
- `cake` => `کیک`
- `juice` => `آبمیوه`

Photo analysis runs only when the admin product payload uses `input_mode=photo_processing`.
Inference is fully local. No external API or hosted vision service is used.

### Runtime configuration

Set these environment variables if you want to customize inference:

```powershell
$env:VISION_ENABLED="1"
$env:VISION_MODEL_PATH="C:\path\to\product_classifier.pt"
$env:VISION_CONFIDENCE_THRESHOLD="0.72"
$env:VISION_TOP_K="3"
$env:VISION_DEVICE="auto"
```

Structured analysis is stored on `Product.photo_analysis` and returned by product serializers. Example:

```json
{
  "success": true,
  "detections": [
    {"label": "خرما", "label_key": "date", "confidence": 0.94},
    {"label": "حلوا", "label_key": "halva", "confidence": 0.81}
  ],
  "top_label": "خرما",
  "top_label_key": "date",
  "uncertain": false,
  "error": null,
  "threshold": 0.72,
  "model_version": "product_classifier"
}
```

If the model is missing, corrupt, disabled, or confidence is too low, the API keeps working and returns an uncertain analysis instead of forcing a wrong label.

### Dataset layout

Classifier training expects this folder layout:

```text
data/products/
  train/
    halva/
    date/
    orange/
    tangerine/
    banana/
    cake/
    juice/
  val/
    halva/
    date/
    orange/
    tangerine/
    banana/
    cake/
    juice/
```

For future object detection, keep the same class keys and add a separate detection dataset, for example:

```text
data/products_detection/
  images/
    train/
    val/
  labels/
    train/
    val/
```

The current architecture is classifier-first with tile-based multi-region inference so it can be upgraded to a detector later without changing the Django integration layer.

### Train locally

Run the management command from `backend/`:

```powershell
..\backend\.venv\Scripts\python manage.py train_product_classifier `
  --data-root data/products `
  --output models/product_classifier.pt `
  --epochs 8 `
  --batch-size 16 `
  --learning-rate 0.001 `
  --image-size 224
```

After training, point `VISION_MODEL_PATH` to the generated `.pt` file.

## Admin CSRF on Production

If admin login returns `403 CSRF verification failed` on hosted domains, set:

- `CSRF_TRUSTED_ORIGINS` (comma-separated, with scheme), e.g.
  - `https://packetop.runflare.run,https://your-domain.com`
- `DJANGO_ALLOWED_HOSTS` to include your domain(s).

This project also enables reverse-proxy headers by default:

- `USE_X_FORWARDED_HOST=1`
- `SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')`

In addition, CSRF middleware is proxy-aware and domain-agnostic:

- It accepts requests when `Origin` matches `Host`/`X-Forwarded-Host`.
- This avoids hardcoding one fixed domain when your host/domain changes.

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

## Telegram Bot

Private admin bot support is implemented in `backend/telegram_bot`.

Core commands:

- `/start`, `/help`, `/ping`, `/whoami`, `/status`, `/health`
- `/dashboard`
- `/products [query]`, `/product <slug-or-id>`
- `/feature <slug-or-id>`, `/unfeature <slug-or-id>`
- `/activate <slug-or-id>`, `/deactivate <slug-or-id>`
- `/orders [status]`, `/order <public_id>`
- `/orderstatus <public_id> <status>`
- `/settings`

Run polling:

```powershell
..\backend\.venv\Scripts\python manage.py run_telegram_bot
```

Configure webhook:

```powershell
..\backend\.venv\Scripts\python manage.py configure_telegram_webhook
```

Send order notifications:

```powershell
..\backend\.venv\Scripts\python manage.py telegram_notify_new_orders
```

See `docs/TELEGRAM_BOT.md` for the security model and env vars.

# API Contract (v1)

Base URL (dev): `http://localhost:8000`

API prefix: `/api/v1`

## Auth Rules

- Public endpoints: no auth required.
- Admin endpoints:
  - Require `Authorization: Bearer <access_token>`
  - User must be `is_staff=true`
- Token endpoints use `djangorestframework-simplejwt`.

## Common Conventions

- Content type: `application/json`
- IDs:
  - Domain entity IDs are UUID strings
  - Orders are tracked by `public_id` (e.g. `ORD-AB12CD34`)
- Money fields are integer Tomans.
- Date/time:
  - `created_at`: ISO datetime
  - delivery `date`: `YYYY-MM-DD`

## Public Endpoints

## 1) Categories

- `GET /api/v1/categories/`

Response `200`:

```json
[
  {
    "id": "uuid",
    "name": "اقتصادی",
    "slug": "economic",
    "icon": "💰"
  }
]
```

## 2) Products List

- `GET /api/v1/products/`

Query params:

- `category` (uuid) -> filter by category ID
- `event_type` (string) -> filter by product event type
- `featured` (`true|false`)
- `available` (`true|false`)
- `search` (string; matches name/description/contents)

Response `200`:

```json
[
  {
    "id": "uuid",
    "name": "پک اقتصادی همایش",
    "description": "....",
    "price": 85000,
    "category_ids": ["uuid"],
    "event_types": ["conference"],
    "contents": ["..."],
    "image": "/media/products/x.jpg",
    "featured": true,
    "available": true
  }
]
```

## 3) Product Detail

- `GET /api/v1/products/{id}/`

Response `200`: same shape as list item.
Response `404` if not found.

## 4) Builder Items

- `GET /api/v1/builder-items/`

Response `200`:

```json
[
  {
    "id": "uuid",
    "name": "زیپ‌لاک",
    "group": "packaging",
    "price": 15000,
    "required": true,
    "image": null
  }
]
```

## 5) Site Settings (Singleton)

- `GET /api/v1/settings/`

Response `200`:

```json
{
  "min_order_qty": 40,
  "lead_time_hours": 48,
  "allowed_provinces": ["تهران", "البرز"],
  "delivery_windows": ["10-12", "12-14"],
  "payment_methods": [
    { "id": "pay-later", "label": "پرداخت بعد از تایید", "enabled": true }
  ]
}
```

## 6) Create Order

- `POST /api/v1/orders/`

Request body:

```json
{
  "items": [
    {
      "product_id": "uuid-or-null",
      "name": "پک اقتصادی",
      "quantity": 40,
      "price": 85000,
      "is_custom_pack": false,
      "custom_config": null
    }
  ],
  "customer": {
    "name": "نام مشتری",
    "phone": "09123456789",
    "province": "تهران",
    "address": "آدرس کامل",
    "notes": "اختیاری"
  },
  "delivery": {
    "date": "2026-02-20",
    "window": "12-14"
  },
  "payment_method": "pay-later"
}
```

Response `201`:

```json
{
  "public_id": "ORD-AB12CD34",
  "status": "pending",
  "customer": {
    "name": "نام مشتری",
    "phone": "09123456789",
    "province": "تهران",
    "address": "آدرس کامل",
    "notes": "اختیاری"
  },
  "delivery": {
    "date": "2026-02-20",
    "window": "12-14"
  },
  "payment_method": "pay-later",
  "total": 3400000,
  "created_at": "2026-02-12T10:00:00Z",
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid-or-null",
      "name": "پک اقتصادی",
      "quantity": 40,
      "price": 85000,
      "is_custom_pack": false,
      "custom_config": null
    }
  ],
  "notes": []
}
```

Validation rules (server-side):

- `items` must be non-empty
- `quantity >= 1` per item
- phone must match mobile format
- province must be in allowed settings provinces
- delivery date must respect lead-time rules
- payment method must be enabled in settings

## 7) Public Order Tracking

- `GET /api/v1/orders/{public_id}/`

Response `200`: same shape as create response.
Response `404` if not found.

## Admin Auth Endpoints

## 8) Obtain JWT

- `POST /api/v1/auth/token/`

Request:

```json
{
  "username": "admin",
  "password": "your-password"
}
```

Response `200`:

```json
{
  "access": "<jwt>",
  "refresh": "<jwt>"
}
```

## 9) Refresh JWT

- `POST /api/v1/auth/token/refresh/`

Request:

```json
{
  "refresh": "<jwt>"
}
```

Response `200`:

```json
{
  "access": "<jwt>"
}
```

## Admin Endpoints (JWT + staff required)

## 10) List Orders (Admin)

- `GET /api/v1/admin/orders/`

Optional query params:

- `status`
- `search` (matches `public_id`, customer name, phone)

Response `200`: list of full order objects.

## 11) Update Order Status (Admin)

- `PATCH /api/v1/admin/orders/{public_id}/`

Request:

```json
{
  "status": "confirmed"
}
```

Allowed statuses:

- `pending`
- `confirmed`
- `preparing`
- `shipped`
- `delivered`

Response `200`: updated order object.

## 12) Add Order Note (Admin)

- `POST /api/v1/admin/orders/{public_id}/notes/`

Request:

```json
{
  "note": "تماس با مشتری انجام شد"
}
```

Response `201`:

```json
{
  "id": "uuid",
  "note": "تماس با مشتری انجام شد",
  "created_at": "2026-02-12T11:00:00Z"
}
```

## API Documentation

- `GET /api/schema/` -> OpenAPI schema
- `GET /api/docs/` -> Swagger UI

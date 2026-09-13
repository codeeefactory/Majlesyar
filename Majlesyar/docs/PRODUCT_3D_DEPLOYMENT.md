# استقرار تولیدی سه‌بعدی

Worker مدل‌سازی تصویر به GLB روی Modal با نام `majlesyar-product-3d` مستقر شده است.

## تنظیم بک‌اند

در `.env.production` سرور Django این مقادیر را بگذارید:

```text
PRODUCT_3D_GENERATOR_URL=https://sajjad-rgz--majlesyar-product-3d-worker-api.modal.run/generate
PRODUCT_3D_GENERATOR_TOKEN=<همان مقدار PRODUCT_3D_GENERATOR_TOKEN در Modal>
PRODUCT_3D_GENERATOR_MODEL=triposr
PRODUCT_3D_GENERATOR_TIMEOUT=600
PRODUCT_3D_MAX_BYTES=26214400
```

سپس داخل کانتینر بک‌اند اجرا کنید:

```bash
python manage.py migrate --noinput
python manage.py generate_product_3d_models --include-builder-items
```

فرمان بالا فقط محصولاتی را پردازش می‌کند که مدل آماده ندارند. برای بازتولید همهٔ مدل‌ها از `--all` استفاده کنید.

## بررسی سلامت

```bash
curl https://sajjad-rgz--majlesyar-product-3d-worker-api.modal.run/health
```

پاسخ سالم باید `ok: true` و `device: cuda:0` داشته باشد. مسیر `/generate` خصوصی است و بدون Bearer token باید `401` برگرداند.

## نکتهٔ استقرار

انتشار کد در GitHub به‌تنهایی دیتابیس/کانتینر production را به‌روزرسانی نمی‌کند. بعد از در دسترس بودن SSH یا پنل Docker، image جدید را deploy کنید، migration را اجرا کنید و سپس batch بالا را یک‌بار اجرا نمایید.

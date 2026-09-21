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
PRODUCT_IMAGE_ANALYZER_URL=https://sajjad-rgz--majlesyar-product-3d-worker-api.modal.run/analyze
PRODUCT_IMAGE_ANALYZER_TIMEOUT=180
```

سپس داخل کانتینر بک‌اند اجرا کنید:

```bash
python manage.py migrate --noinput
python manage.py generate_product_3d_models --include-builder-items
```

فرمان بالا فقط محصولاتی را پردازش می‌کند که مدل آماده ندارند. برای بازتولید همهٔ مدل‌ها از `--all` استفاده کنید.

## پردازش خودکار بارگذاری‌های جدید

سرویس `media-worker` در `docker-compose.prod.yml` صف پایدار دیتابیس را پردازش می‌کند. ذخیرهٔ هر عکس جدید محصول یا آیتم سازنده، بدون معطل‌کردن درخواست وب، این کارها را صف می‌کند:

- تحلیل GPU تصویر و ذخیره در `photo_analysis`
- تطبیق تک‌تک `contents` پک با خروجی مدل و ذخیرهٔ نتیجه
- ساخت GLB و ذخیره در volume رسانه
- سه بار تلاش با backoff و بازیابی jobهای متوقف‌شده

برای تحلیل داده‌های موجود بدون بازسازی GLBها:

```bash
python manage.py enqueue_asset_jobs
python manage.py process_asset_jobs
```

برای worker دائم خارج از Compose:

```bash
python manage.py process_asset_jobs --loop --poll-interval 5
```

آپلودهای production به‌صورت خودکار «training candidate» ثبت می‌شوند. آموزش خودکار روی پیش‌بینی‌های بدون برچسب عمداً انجام نمی‌شود؛ این کار خطاهای مدل را به دادهٔ آموزشی برمی‌گرداند. آموزش واقعی فقط از dataset تاییدشده با `train_product_classifier` انجام می‌شود.

## بررسی سلامت

```bash
curl https://sajjad-rgz--majlesyar-product-3d-worker-api.modal.run/health
```

پاسخ سالم باید `ok: true` و `device: cuda:0` داشته باشد. مسیر `/generate` خصوصی است و بدون Bearer token باید `401` برگرداند.

## نکتهٔ استقرار

انتشار کد در GitHub به‌تنهایی دیتابیس/کانتینر production را به‌روزرسانی نمی‌کند. بعد از در دسترس بودن SSH یا پنل Docker، image جدید را deploy کنید، migration را اجرا کنید و سپس batch بالا را یک‌بار اجرا نمایید.

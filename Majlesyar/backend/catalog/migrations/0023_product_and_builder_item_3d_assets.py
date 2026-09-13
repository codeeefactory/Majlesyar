from django.db import migrations, models

import catalog.three_d


class Migration(migrations.Migration):
    dependencies = [("catalog", "0022_sync_existing_product_page_assignments")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="model_3d",
            field=models.FileField(blank=True, help_text="مدل GLB تاییدشده را بارگذاری کنید؛ در نبود آن پیش‌نمایش حجمی از عکس محصول ساخته می‌شود.", max_length=500, null=True, upload_to=catalog.three_d.build_asset_3d_upload_path, validators=[catalog.three_d.validate_glb_file], verbose_name="مدل سه‌بعدی محصول (GLB)"),
        ),
        migrations.AddField(model_name="product", name="model_3d_status", field=models.CharField(choices=[("missing", "ساخته نشده"), ("processing", "در حال ساخت"), ("ready", "آماده"), ("failed", "خطا در ساخت")], default="missing", max_length=20, verbose_name="وضعیت مدل سه‌بعدی")),
        migrations.AddField(model_name="product", name="model_3d_metadata", field=models.JSONField(blank=True, default=dict, verbose_name="اطلاعات تولید مدل سه‌بعدی")),
        migrations.AddField(model_name="product", name="model_3d_error", field=models.TextField(blank=True, default="", verbose_name="خطای تولید مدل سه‌بعدی")),
        migrations.AddField(
            model_name="builderitem",
            name="model_3d",
            field=models.FileField(blank=True, help_text="اختیاری؛ اگر خالی باشد تصویر آیتم به‌صورت پیش‌نمایش حجمی نمایش داده می‌شود.", max_length=500, null=True, upload_to=catalog.three_d.build_asset_3d_upload_path, validators=[catalog.three_d.validate_glb_file], verbose_name="مدل سه‌بعدی آیتم (GLB)"),
        ),
        migrations.AddField(model_name="builderitem", name="model_3d_status", field=models.CharField(choices=[("missing", "ساخته نشده"), ("processing", "در حال ساخت"), ("ready", "آماده"), ("failed", "خطا در ساخت")], default="missing", max_length=20, verbose_name="وضعیت مدل سه‌بعدی")),
        migrations.AddField(model_name="builderitem", name="model_3d_metadata", field=models.JSONField(blank=True, default=dict, verbose_name="اطلاعات تولید مدل سه‌بعدی")),
        migrations.AddField(model_name="builderitem", name="model_3d_error", field=models.TextField(blank=True, default="", verbose_name="خطای تولید مدل سه‌بعدی")),
    ]

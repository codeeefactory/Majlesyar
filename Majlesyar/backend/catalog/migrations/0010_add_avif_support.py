import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_product_photo_analysis"),
    ]

    operations = [
        migrations.AlterField(
            model_name="builderitem",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="نکته: بارگذاری تصویر با فرمت‌های jpg، jpeg، png، webp یا avif برای نمایش بهتر این آیتم.",
                null=True,
                upload_to="builder-items/",
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))],
                verbose_name="تصویر",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="راهنما: لوگو دسته بندی را با فرمت‌های jpg، jpeg، png، webp یا avif بارگذاری کنید.",
                null=True,
                upload_to="category-logos/",
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))],
                verbose_name="لوگو",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="راهنما: تصویر محصول را با کیفیت مناسب و فرمت‌های jpg، jpeg، png، webp یا avif بارگذاری کنید. می توانید با گزینه پاک کردن، انتخاب تصویر را حذف کنید.",
                null=True,
                upload_to="products/",
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "avif"))],
                verbose_name="تصویر محصول",
            ),
        ),
    ]

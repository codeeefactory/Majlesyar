import uuid

import catalog.image_utils
from django.db import migrations, models
import django.core.validators


EVENT_PARENT_PATHS = {
    "memorial": "/pack/memorial",
    "pack": "/pack",
    "pack-personal": "/pack/personal",
    "pack-memorial-luxury": "/pack/memorial/luxury",
    "halva-khorma": "/halva-khorma",
    "halva-khorma-luxury": "/halva-khorma/luxury",
    "conference": "/food/finger_food",
    "food": "/food",
    "party": "/flower",
    "memorial-wreaths": "/flower/memorial-wreaths",
    "bouquets": "/flower/bouquets",
    "congratulatory-wreaths": "/flower/congratulatory-wreaths",
    "flower-congratulation-wreaths": "/flower/congratulatory-wreaths",
    "flower-box": "/flower/box",
}


def populate_public_paths_and_fix_known_categories(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Category = apps.get_model("catalog", "Category")

    known_fixes = {
        "پک پذیرایی": ["memorial"],
        "حلوا مجلسی سینی بزرگ": ["halva-khorma"],
    }
    for product_name, slugs in known_fixes.items():
        for product in Product.objects.filter(name__iexact=product_name):
            categories = Category.objects.filter(slug__in=slugs)
            product.categories.set(categories)
            product.event_types = slugs
            product.save(update_fields=["event_types"])

    used_paths = set()
    for product in Product.objects.order_by("created_at", "id"):
        event_types = [str(item).strip() for item in (product.event_types or []) if str(item).strip()]
        parent_path = next((EVENT_PARENT_PATHS[item] for item in event_types if item in EVENT_PARENT_PATHS), "/pack")
        base_path = f"{parent_path.rstrip('/')}/{product.url_slug}"
        candidate = base_path
        suffix = 2
        while candidate in used_paths:
            candidate = f"{base_path}-{suffix}"
            suffix += 1
        product.public_path = candidate
        product.save(update_fields=["public_path"])
        used_paths.add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0019_alter_product_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="public_path",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="آدرس کامل محصول"),
            preserve_default=False,
        ),
        migrations.RunPython(populate_public_paths_and_fix_known_categories, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="public_path",
            field=models.CharField(
                blank=True,
                help_text="کل آدرس یا مسیر را وارد کنید؛ مثل https://majlesyar.com/pack/my-pack یا /pack/my-pack. مسیرهای /product مجاز نیستند.",
                max_length=500,
                unique=True,
                verbose_name="آدرس کامل محصول",
            ),
        ),
        migrations.CreateModel(
            name="InternalLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_path", models.CharField(db_index=True, help_text="مسیر صفحه‌ای که کارت در آن نمایش داده شود؛ مثل /pack/memorial.", max_length=500, verbose_name="صفحه نمایش‌دهنده")),
                ("label", models.CharField(max_length=255, verbose_name="عنوان کارت")),
                ("target_url", models.CharField(help_text="مسیر داخلی مقصد؛ مثل /builder یا /flower/memorial-wreaths.", max_length=500, verbose_name="لینک مقصد")),
                ("image", models.ImageField(blank=True, help_text="تصویر را هر زمان خواستید جایگزین یا پاک کنید.", null=True, upload_to="internal-links/%Y/%m/", validators=[catalog.image_utils.image_extension_validator], verbose_name="تصویر کارت")),
                ("image_alt", models.CharField(blank=True, default="", help_text="توضیح کوتاه و دقیق تصویر برای دسترس‌پذیری و سئو.", max_length=255, verbose_name="متن جایگزین تصویر (Alt)")),
                ("position", models.PositiveIntegerField(default=100, validators=[django.core.validators.MinValueValidator(1)], verbose_name="ترتیب نمایش")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "لینک داخلی تصویری",
                "verbose_name_plural": "لینک‌های داخلی تصویری",
                "ordering": ["source_path", "position", "created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="internallink",
            constraint=models.UniqueConstraint(fields=("source_path", "target_url"), name="unique_internal_link_per_source"),
        ),
    ]

import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0013_product_image_variants"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerReview",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="نکته: این شناسه به صورت خودکار ساخته می شود.",
                        primary_key=True,
                        serialize=False,
                        verbose_name="شناسه",
                    ),
                ),
                (
                    "customer_name",
                    models.CharField(
                        help_text="نام نمایشی مشتری برای سایت.",
                        max_length=120,
                        verbose_name="نام مشتری",
                    ),
                ),
                (
                    "customer_city",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="شهر یا محدوده مشتری، اختیاری.",
                        max_length=80,
                        verbose_name="شهر",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="عنوان کوتاه برای نظر مشتری.",
                        max_length=160,
                        verbose_name="عنوان نظر",
                    ),
                ),
                (
                    "comment",
                    models.TextField(
                        help_text="متن کامل بازخورد مشتری.",
                        verbose_name="متن نظر",
                    ),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text="امتیاز از ۱ تا ۵.",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                        verbose_name="امتیاز",
                    ),
                ),
                (
                    "is_approved",
                    models.BooleanField(
                        default=True,
                        help_text="فقط نظرهای تایید شده در سایت نمایش داده می شوند.",
                        verbose_name="تایید شده",
                    ),
                ),
                (
                    "is_featured",
                    models.BooleanField(
                        default=False,
                        help_text="نظرهای ویژه در بخش بازخورد مشتریان اولویت دارند.",
                        verbose_name="ویژه",
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(
                        default=100,
                        help_text="عدد کوچکتر یعنی نمایش زودتر.",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="ترتیب نمایش",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        help_text="اگر نظر مربوط به یک محصول خاص است، آن محصول را انتخاب کنید.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="customer_reviews",
                        to="catalog.product",
                        verbose_name="محصول",
                    ),
                ),
            ],
            options={
                "verbose_name": "نظر مشتری",
                "verbose_name_plural": "نظرهای مشتریان",
                "ordering": ["display_order", "-is_featured", "-created_at"],
            },
        ),
    ]

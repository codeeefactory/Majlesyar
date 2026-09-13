from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0016_product_utf8_image_upload_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="builder_display_order",
            field=models.PositiveIntegerField(
                default=100,
                help_text="نکته: عدد کوچکتر یعنی نمایش زودتر در صفحه ساخت پک.",
                validators=[MinValueValidator(1)],
                verbose_name="ترتیب نمایش در سازنده پک",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="builder_group",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "تشخیص خودکار"),
                    ("packaging", "بسته بندی"),
                    ("fruit", "میوه"),
                    ("drink", "نوشیدنی"),
                    ("snack", "اسنک"),
                    ("addon", "افزودنی"),
                    ("products", "محصولات آماده"),
                ],
                default="",
                help_text="نکته: با حالت تشخیص خودکار، بخش محصول از دسته‌بندی و متن محصول حدس زده می‌شود.",
                max_length=20,
                verbose_name="بخش محصول در سازنده پک",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="builder_required",
            field=models.BooleanField(
                default=False,
                help_text="نکته: برای محصولات معمولاً خاموش بماند؛ فقط وقتی روشن کنید که این محصول باید در پک انتخاب شود.",
                verbose_name="انتخاب اجباری در سازنده پک",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="show_in_builder",
            field=models.BooleanField(
                default=True,
                help_text="نکته: اگر فعال باشد، این محصول در صفحه ساخت پک اختصاصی (/builder) قابل انتخاب است.",
                verbose_name="نمایش در سازنده پک",
            ),
        ),
    ]

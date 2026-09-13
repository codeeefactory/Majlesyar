from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_product_builder_display_controls"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_temporary",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "راهنما: برای محصول آزمایشی فعال کنید. صفحه محصول در سایت قابل بررسی می‌ماند، "
                    "اما به موتورهای جستجو دستور داده می‌شود آن را ایندکس یا دنبال نکنند."
                ),
                verbose_name="محصول موقت (عدم نمایش در گوگل)",
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_category_color_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="photo_analysis",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="خروجی ساختارمند تشخیص محلی تصویر محصول.",
                verbose_name="نتیجه تحلیل تصویر",
            ),
        ),
    ]

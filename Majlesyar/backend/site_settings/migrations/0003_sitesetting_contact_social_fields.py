from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0002_alter_sitesetting_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="contact_phone",
            field=models.CharField(blank=True, default="+989915505141", max_length=32),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="contact_address",
            field=models.TextField(
                blank=True,
                default="تهران، امیرآباد، خیابان کارگر شمالی، خیابان فرشی مقدم(شانزدهم)، پلاک ۹۱، واحد۶.",
            ),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="working_hours",
            field=models.CharField(blank=True, default="شنبه تا پنجشنبه ۹ صبح تا ۹ شب", max_length=255),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="instagram_url",
            field=models.URLField(blank=True, default="https://instagram.com/majlesyar", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="telegram_url",
            field=models.URLField(blank=True, default="https://t.me/majlesyar", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="whatsapp_url",
            field=models.URLField(blank=True, default="https://wa.me/989915505141", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="bale_url",
            field=models.URLField(blank=True, default="https://ble.ir/majlesyar", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="maps_url",
            field=models.URLField(blank=True, default="https://maps.google.com/?q=Tehran,Valiasr", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="maps_embed_url",
            field=models.URLField(
                blank=True,
                default="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s",
                max_length=1000,
            ),
        ),
    ]

from django.db import migrations, models


def update_existing_contact_defaults(apps, schema_editor):
    SiteSetting = apps.get_model("site_settings", "SiteSetting")
    SiteSetting.objects.filter(contact_phone="+989915505141").update(contact_phone="09122148354")
    SiteSetting.objects.filter(whatsapp_url="https://wa.me/989915505141").update(
        whatsapp_url="https://wa.me/989122148354"
    )


def restore_previous_contact_defaults(apps, schema_editor):
    SiteSetting = apps.get_model("site_settings", "SiteSetting")
    SiteSetting.objects.filter(contact_phone="09122148354").update(contact_phone="+989915505141")
    SiteSetting.objects.filter(whatsapp_url="https://wa.me/989122148354").update(
        whatsapp_url="https://wa.me/989915505141"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0005_sitesetting_event_pages_sitesetting_page_seo_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesetting",
            name="contact_phone",
            field=models.CharField(blank=True, default="09122148354", max_length=32),
        ),
        migrations.AlterField(
            model_name="sitesetting",
            name="whatsapp_url",
            field=models.URLField(blank=True, default="https://wa.me/989122148354", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="eitaa_url",
            field=models.URLField(blank=True, default="https://eitaa.com/majlesyar", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="soroush_url",
            field=models.URLField(blank=True, default="https://splus.ir/majlesyar", max_length=500),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="rubika_url",
            field=models.URLField(blank=True, default="https://rubika.ir/majlesyar", max_length=500),
        ),
        migrations.RunPython(update_existing_contact_defaults, restore_previous_contact_defaults),
    ]

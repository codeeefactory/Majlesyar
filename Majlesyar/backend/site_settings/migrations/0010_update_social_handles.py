from django.db import migrations


SOCIAL_LINKS = {
    "instagram_url": "https://instagram.com/majles.yar",
    "telegram_url": "https://t.me/majlesyar",
    "whatsapp_url": "https://wa.me/989122148354",
    "bale_url": "https://ble.ir/Majlesyar",
    "eitaa_url": "https://eitaa.com/majlesyarr",
    "soroush_url": "https://splus.ir/majlesyar",
    "rubika_url": "https://rubika.ir/majlesyar",
}


def update_social_handles(apps, schema_editor):
    SiteSetting = apps.get_model("site_settings", "SiteSetting")
    SiteSetting.objects.all().update(**SOCIAL_LINKS)


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0009_social_links_to_contact_number"),
    ]

    operations = [
        migrations.RunPython(update_social_handles, migrations.RunPython.noop),
    ]

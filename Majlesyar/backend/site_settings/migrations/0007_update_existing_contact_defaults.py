from django.db import migrations


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
        ("site_settings", "0006_sitesetting_extra_social_links_and_phone"),
    ]

    operations = [
        migrations.RunPython(update_existing_contact_defaults, restore_previous_contact_defaults),
    ]

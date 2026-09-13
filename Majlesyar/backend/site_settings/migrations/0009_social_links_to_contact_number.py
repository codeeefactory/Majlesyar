from django.db import migrations, models


DIRECT_CONTACT_LINKS = {
    "instagram_url": "https://instagram.com/majles.yar",
    "telegram_url": "https://t.me/majlesyar",
    "whatsapp_url": "https://wa.me/989122148354",
    "bale_url": "https://ble.ir/Majlesyar",
    "eitaa_url": "https://eitaa.com/majlesyarr",
    "soroush_url": "https://splus.ir/majlesyar",
    "rubika_url": "https://rubika.ir/majlesyar",
}


def update_contact_links(apps, schema_editor):
    SiteSetting = apps.get_model("site_settings", "SiteSetting")
    for setting in SiteSetting.objects.all():
        pages = list(setting.event_pages or [])
        for page in pages:
            if not isinstance(page, dict):
                continue
            route_path = str(page.get("route_path") or "").rstrip("/")
            if route_path in {"/flower/congratulatory-wreaths", "/flower/congratulation-wreaths", "/flower/box"}:
                page["hidden"] = False
            if route_path == "/pack/memorial" and not page.get("internal_links"):
                page["internal_links"] = [
                    {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
                    {"label": "تاج گل‌های ترحیم و تسلیت", "url": "/flower/memorial-wreaths"},
                    {"label": "فینگر فود", "url": "/food/finger_food"},
                    {"label": "ساخت پک اختصاصی", "url": "/builder"},
                ]
        for field_name, url in DIRECT_CONTACT_LINKS.items():
            setattr(setting, field_name, url)
        setting.event_pages = pages
        setting.save(update_fields=[*DIRECT_CONTACT_LINKS.keys(), "event_pages"])


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0008_alter_sitesetting_allowed_provinces_and_more"),
    ]

    operations = [
        migrations.RunPython(update_contact_links, migrations.RunPython.noop),
        *[
            migrations.AlterField(
                model_name="sitesetting",
                name=field_name,
                field=models.URLField(blank=True, default=url, max_length=500, verbose_name={
                    "instagram_url": "لینک اینستاگرام",
                    "telegram_url": "لینک تلگرام",
                    "whatsapp_url": "لینک واتساپ",
                    "bale_url": "لینک بله",
                    "eitaa_url": "لینک ایتا",
                    "soroush_url": "لینک سروش",
                    "rubika_url": "لینک روبیکا",
                }[field_name]),
            )
            for field_name, url in DIRECT_CONTACT_LINKS.items()
        ],
    ]

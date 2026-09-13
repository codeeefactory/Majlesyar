from django.db import migrations


REQUIRED_EVENT_PAGES = (
    {
        "id": "memorial",
        "slug": "memorial",
        "name": "ترحیم",
        "route_path": "/pack/memorial",
    },
    {
        "id": "party",
        "slug": "party",
        "name": "گل",
        "route_path": "/flower",
    },
)


def restore_core_event_pages(apps, schema_editor):
    SiteSetting = apps.get_model("site_settings", "SiteSetting")
    for setting in SiteSetting.objects.all():
        pages = [page for page in (setting.event_pages or []) if isinstance(page, dict)]
        existing_routes = {
            str(page.get("route_path") or "").rstrip("/") or "/"
            for page in pages
        }
        changed = False
        for required_page in REQUIRED_EVENT_PAGES:
            if required_page["route_path"] in existing_routes:
                continue
            pages.append(dict(required_page))
            changed = True
        if changed:
            setting.event_pages = pages
            setting.save(update_fields=["event_pages"])


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0010_update_social_handles"),
    ]

    operations = [
        migrations.RunPython(restore_core_event_pages, migrations.RunPython.noop),
    ]

from django.db import migrations


OLD_PUBLIC_PATH = "/flower/fruit"
NEW_PUBLIC_PATH = "/pack/memorial/fruit"


def fix_memorial_fruit_product_route(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Product.objects.filter(public_path=OLD_PUBLIC_PATH).update(
        public_path=NEW_PUBLIC_PATH,
        event_types=["memorial"],
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0020_product_public_path_and_internal_links"),
    ]

    operations = [
        migrations.RunPython(fix_memorial_fruit_product_route, migrations.RunPython.noop),
    ]

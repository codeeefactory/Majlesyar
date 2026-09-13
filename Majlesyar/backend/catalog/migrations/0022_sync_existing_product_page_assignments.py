from django.db import migrations


PRODUCT_PAGE_SLUGS = {
    "conference",
    "memorial",
    "halva-khorma",
    "party",
    "food",
    "food-charcuterie-board",
    "food-ashe-rashteh",
    "food-dessert",
    "food-juice",
    "shaleh-zard",
    "pack",
    "pack-personal",
    "pack-memorial-luxury",
    "halva-khorma-luxury",
    "memorial-wreaths",
    "bouquets",
    "congratulatory-wreaths",
    "flower-congratulation-wreaths",
    "flower-funeral-bouquet",
    "flower-box",
}


def sync_existing_product_page_assignments(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")

    for product in Product.objects.prefetch_related("categories").iterator(chunk_size=200):
        page_slugs = list(
            product.categories.filter(slug__in=PRODUCT_PAGE_SLUGS)
            .order_by("slug")
            .values_list("slug", flat=True)
        )
        if product.event_types != page_slugs:
            Product.objects.filter(pk=product.pk).update(event_types=page_slugs)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0021_fix_memorial_fruit_product_route"),
    ]

    operations = [
        migrations.RunPython(
            sync_existing_product_page_assignments,
            migrations.RunPython.noop,
        ),
    ]

from django.core.management.base import BaseCommand

from catalog.models import Product, ensure_event_categories, sync_product_categories


class Command(BaseCommand):
    help = "Ensure all existing products are linked to their inferred event categories."

    def handle(self, *args, **options):
        ensure_event_categories()
        updated = 0

        for product in Product.objects.prefetch_related("categories").all():
            before_ids = set(product.categories.values_list("id", flat=True))
            before_event_types = list(product.event_types or [])
            sync_product_categories(product, force=False)
            after_ids = set(product.categories.values_list("id", flat=True))
            product.refresh_from_db(fields=["event_types"])
            if after_ids != before_ids or list(product.event_types or []) != before_event_types:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Synchronized product categories for {updated} products."))

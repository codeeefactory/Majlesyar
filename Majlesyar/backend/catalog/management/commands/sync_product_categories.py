from django.core.management.base import BaseCommand

from catalog.models import Product, sync_product_categories


class Command(BaseCommand):
    help = "Ensure all existing products are linked to their inferred event categories."

    def handle(self, *args, **options):
        updated = 0

        for product in Product.objects.prefetch_related("categories").all():
            before_ids = set(product.categories.values_list("id", flat=True))
            sync_product_categories(product, force=False)
            after_ids = set(product.categories.values_list("id", flat=True))
            if after_ids != before_ids:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Synchronized product categories for {updated} products."))

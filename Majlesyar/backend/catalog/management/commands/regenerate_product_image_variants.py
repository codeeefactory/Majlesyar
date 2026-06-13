from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from catalog.image_variants import ensure_product_image_variants
from catalog.models import Product


class Command(BaseCommand):
    help = "Generate or regenerate responsive AVIF/WebP/JPEG variants for product images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate variants even when the current image signature already has variants.",
        )
        parser.add_argument(
            "--product",
            action="append",
            default=[],
            help="Filter by product UUID or url_slug. Repeat for multiple products.",
        )

    def handle(self, *args, **options):
        force = bool(options["force"])
        filters = [value.strip() for value in options["product"] if str(value).strip()]
        queryset = Product.objects.all().order_by("name")

        if filters:
            combined_query = Q()
            for value in filters:
                combined_query |= Q(url_slug=value)
                try:
                    combined_query |= Q(id=uuid.UUID(value))
                except (ValueError, TypeError):
                    pass
            queryset = Product.objects.filter(combined_query).distinct().order_by("name")
            if not queryset.exists():
                raise CommandError("No products matched the provided --product filters.")

        processed = 0
        skipped = 0
        original_total = 0
        fallback_total = 0

        for product in queryset:
            if not product.image:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipping {product.name}: no image"))
                continue

            metadata = ensure_product_image_variants(product, force=force)
            Product.objects.filter(pk=product.pk).update(image_variants=metadata)
            product.image_variants = metadata

            original_bytes = int(((metadata.get("original") or {}).get("bytes")) or 0)
            fallback_width = int((((metadata.get("fallback") or {}).get("width")) or 0))
            fallback_variants = (metadata.get("variants") or {}).get("jpeg") or []
            fallback_variant = next((item for item in fallback_variants if int(item.get("width") or 0) == fallback_width), None)
            fallback_bytes = int((fallback_variant or {}).get("bytes") or 0)

            original_total += original_bytes
            fallback_total += fallback_bytes
            processed += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"{product.name}: original {original_bytes / 1024:.1f} KiB -> "
                    f"fallback {fallback_bytes / 1024:.1f} KiB"
                )
            )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Image optimization summary"))
        self.stdout.write(f"Processed: {processed}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Original total: {original_total / 1024:.1f} KiB")
        self.stdout.write(f"Fallback total: {fallback_total / 1024:.1f} KiB")
        if original_total and fallback_total:
            savings = original_total - fallback_total
            self.stdout.write(f"Estimated fallback savings: {savings / 1024:.1f} KiB")

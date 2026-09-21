from __future__ import annotations

from django.core.management.base import BaseCommand

from catalog.media_processing import enqueue_asset_processing
from catalog.models import AssetProcessingJob, BuilderItem, Product


class Command(BaseCommand):
    help = "Queue image analysis for existing products and builder items without blocking web requests."

    def add_arguments(self, parser):
        parser.add_argument("--force-3d", action="store_true", help="Regenerate GLB files as well as image analysis.")
        parser.add_argument("--force", action="store_true", help="Requeue assets that were already analyzed.")
        parser.add_argument("--products-only", action="store_true")
        parser.add_argument("--builder-items-only", action="store_true")

    def handle(self, *args, **options):
        if options["products_only"] and options["builder_items_only"]:
            self.stderr.write(self.style.ERROR("Choose only one target filter."))
            return

        targets = []
        if not options["builder_items_only"]:
            targets.extend(
                (AssetProcessingJob.TargetType.PRODUCT, product.pk)
                for product in Product.objects.exclude(image="").exclude(image__isnull=True).only("pk")
            )
        if not options["products_only"]:
            targets.extend(
                (AssetProcessingJob.TargetType.BUILDER_ITEM, item.pk)
                for item in BuilderItem.objects.exclude(image="").exclude(image__isnull=True).only("pk")
            )

        queued = 0
        for target_type, target_id in targets:
            job = enqueue_asset_processing(
                target_type,
                target_id,
                image_changed=options["force_3d"],
                force_requeue=options["force"],
            )
            if job and job.status == AssetProcessingJob.Status.PENDING:
                queued += 1
        self.stdout.write(self.style.SUCCESS(f"Queued {queued} asset(s)."))

from django.core.management.base import BaseCommand, CommandError

from catalog.models import BuilderItem, Product
from catalog.three_d import generate_asset_3d


class Command(BaseCommand):
    help = "Generate GLB assets for builder products through the configured private ML worker."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Regenerate assets that are already ready.")
        parser.add_argument("--include-builder-items", action="store_true", help="Also process legacy builder items.")
        parser.add_argument("--limit", type=int, default=0, help="Maximum number of records to process (0 = unlimited).")

    def handle(self, *args, **options):
        records = list(Product.objects.filter(available=True, image__isnull=False).exclude(image=""))
        if options["include_builder_items"]:
            records.extend(BuilderItem.objects.filter(image__isnull=False).exclude(image=""))
        if not options["all"]:
            records = [record for record in records if record.model_3d_status != "ready"]
        if options["limit"] > 0:
            records = records[: options["limit"]]

        succeeded = 0
        failed = 0
        for record in records:
            try:
                generate_asset_3d(record, force=options["all"])
                succeeded += 1
                self.stdout.write(self.style.SUCCESS(f"ready: {record.pk} {record.name}"))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"failed: {record.pk} {record.name}: {exc}"))

        self.stdout.write(f"3D generation finished: {succeeded} ready, {failed} failed")
        if failed and not succeeded:
            raise CommandError("No 3D asset could be generated.")

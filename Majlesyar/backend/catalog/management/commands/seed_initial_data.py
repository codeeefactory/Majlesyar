import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import BuilderItem, Category, Product
from site_settings.models import SiteSetting


class Command(BaseCommand):
    help = "Seed initial categories, products, builder items, and settings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file_path",
            default=str(Path("seed") / "initial_data.json"),
            help="Path to seed JSON file relative to backend root.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"Seed file not found: {file_path}"))
            return

        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        categories_by_slug: dict[str, Category] = {}
        for item in payload.get("categories", []):
            category, _ = Category.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "icon": item.get("icon", ""),
                },
            )
            categories_by_slug[category.slug] = category

        for item in payload.get("products", []):
            category_slugs = item.get("category_slugs", [])
            product, _ = Product.objects.update_or_create(
                name=item["name"],
                defaults={
                    "description": item.get("description", ""),
                    "price": item.get("price"),
                    "event_types": item.get("event_types", []),
                    "contents": item.get("contents", []),
                    "featured": item.get("featured", False),
                    "available": item.get("available", True),
                },
            )
            product_categories = [
                categories_by_slug[slug] for slug in category_slugs if slug in categories_by_slug
            ]
            product.categories.set(product_categories)

        for item in payload.get("builder_items", []):
            BuilderItem.objects.update_or_create(
                name=item["name"],
                group=item["group"],
                defaults={
                    "price": item.get("price", 0),
                    "required": item.get("required", True),
                },
            )

        settings_data = payload.get("settings", {})
        site_setting = SiteSetting.load()
        site_setting.min_order_qty = settings_data.get("min_order_qty", site_setting.min_order_qty)
        site_setting.lead_time_hours = settings_data.get(
            "lead_time_hours",
            site_setting.lead_time_hours,
        )
        site_setting.allowed_provinces = settings_data.get("allowed_provinces", [])
        site_setting.delivery_windows = settings_data.get("delivery_windows", [])
        site_setting.payment_methods = settings_data.get("payment_methods", [])
        site_setting.save()

        self.stdout.write(self.style.SUCCESS("Initial data seeded successfully."))

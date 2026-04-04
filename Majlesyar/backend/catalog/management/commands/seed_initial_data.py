import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import BuilderItem, Category, Product, Tag
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
        seed_root = file_path.parent

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

        tags_by_slug: dict[str, Tag] = {}
        for item in payload.get("tags", []):
            tag, _ = Tag.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                },
            )
            tags_by_slug[tag.slug] = tag

        for item in payload.get("products", []):
            category_slugs = item.get("category_slugs", [])
            event_type_slugs = item.get("event_types", [])
            tag_slugs = item.get("tag_slugs", [])
            image_source = item.get("image_source")
            product, _ = Product.objects.update_or_create(
                name=item["name"],
                defaults={
                    "url_slug": item.get("url_slug", ""),
                    "description": item.get("description", ""),
                    "price": item.get("price"),
                    "event_types": item.get("event_types", []),
                    "contents": item.get("contents", []),
                    "image_alt": item.get("image_alt", ""),
                    "image_name": item.get("image_name", ""),
                    "featured": item.get("featured", False),
                    "available": item.get("available", True),
                },
            )
            combined_slugs = list(dict.fromkeys([*category_slugs, *event_type_slugs]))
            product_categories = [
                categories_by_slug[slug] for slug in combined_slugs if slug in categories_by_slug
            ]
            product.categories.set(product_categories)
            product_tags = [tags_by_slug[slug] for slug in tag_slugs if slug in tags_by_slug]
            product.tags.set(product_tags)

            if image_source:
                image_path = (seed_root / image_source).resolve()
                try:
                    image_path.relative_to(seed_root.resolve())
                except ValueError:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipping image outside seed directory for product '{product.name}': {image_source}"
                        )
                    )
                else:
                    if image_path.exists():
                        current_image_name = Path(product.image.name).name if product.image else None
                        if current_image_name != image_path.name:
                            with image_path.open("rb") as image_file:
                                product.image.save(image_path.name, File(image_file), save=True)
                    else:
                        self.stderr.write(
                            self.style.WARNING(
                                f"Image not found for product '{product.name}': {image_source}"
                            )
                        )

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
        site_setting.contact_phone = settings_data.get("contact_phone", site_setting.contact_phone)
        site_setting.contact_address = settings_data.get("contact_address", site_setting.contact_address)
        site_setting.working_hours = settings_data.get("working_hours", site_setting.working_hours)
        site_setting.instagram_url = settings_data.get("instagram_url", site_setting.instagram_url)
        site_setting.telegram_url = settings_data.get("telegram_url", site_setting.telegram_url)
        site_setting.whatsapp_url = settings_data.get("whatsapp_url", site_setting.whatsapp_url)
        site_setting.bale_url = settings_data.get("bale_url", site_setting.bale_url)
        site_setting.maps_url = settings_data.get("maps_url", site_setting.maps_url)
        site_setting.maps_embed_url = settings_data.get("maps_embed_url", site_setting.maps_embed_url)
        site_setting.save()

        self.stdout.write(self.style.SUCCESS("Initial data seeded successfully."))

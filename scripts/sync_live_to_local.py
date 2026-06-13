from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "Majlesyar" / "backend"
ARTIFACTS = ROOT / "artifacts"

sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from django.db import transaction  # noqa: E402

from catalog.models import Category, Product  # noqa: E402
from site_settings.models import SiteSetting  # noqa: E402


LIVE_THEME_PALETTE = {
    "primary": "#0085A3",
    "accent": "#55CEF2",
    "background": "#FCFAF8",
    "surface": "#FFFFFF",
    "foreground": "#2B303B",
    "muted_foreground": "#576175",
    "success": "#1DAF52",
    "warning": "#E7B008",
}


def read_json(name: str):
    text = (ARTIFACTS / name).read_text(encoding="utf-8-sig")
    return json.loads(text)


def remote_filename(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    return name or fallback


def download_image(url: str | None, slug: str) -> str:
    if not url:
        return ""
    filename = remote_filename(url, f"{slug}.webp")
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://majlesyar.com/",
        },
    )
    with urlopen(request, timeout=30) as response:
        content = response.read()
    return filename, content


def sync_categories(categories: list[dict]) -> tuple[int, int]:
    live_ids = [item["id"] for item in categories]
    deleted, _ = Category.objects.exclude(id__in=live_ids).delete()

    upserted = 0
    for item in categories:
        Category.objects.update_or_create(
            id=item["id"],
            defaults={
                "name": item.get("name") or "",
                "slug": item.get("slug") or "",
                "icon": item.get("icon") or "",
                "color": item.get("color") or "",
            },
        )
        upserted += 1
    return upserted, deleted


def sync_products(products: list[dict]) -> tuple[int, int]:
    live_ids = [item["id"] for item in products]
    deleted, _ = Product.objects.exclude(id__in=live_ids).delete()

    upserted = 0
    for item in products:
        product, _created = Product.objects.update_or_create(
            id=item["id"],
            defaults={
                "name": item.get("name") or "",
                "url_slug": item.get("url_slug") or "",
                "description": item.get("description") or "",
                "price": item.get("price"),
                "event_types": item.get("event_types") or [],
                "contents": item.get("contents") or [],
                "image_alt": item.get("image_alt") or "",
                "image_name": item.get("image_name") or "",
                "featured": bool(item.get("featured")),
                "available": bool(item.get("available", True)),
            },
        )

        image_url = item.get("image")
        if image_url:
            try:
                filename, content = download_image(image_url, item.get("url_slug") or str(product.id))
            except URLError as exc:
                print(f"image download skipped for {item.get('url_slug')}: {exc}")
                filename, content = "", b""
            current_name = Path(product.image.name).name if product.image else ""
            if filename and current_name != filename:
                product.image.save(filename, ContentFile(content), save=True)
        elif product.image:
            product.image.delete(save=False)
            product.image = None
            product.save(update_fields=["image", "image_name", "image_alt", "image_variants", "updated_at"])

        category_ids = item.get("category_ids") or []
        product.categories.set(Category.objects.filter(id__in=category_ids))
        upserted += 1
    return upserted, deleted


def sync_settings(settings_payload: dict) -> None:
    settings = SiteSetting.load()
    for field in (
        "min_order_qty",
        "lead_time_hours",
        "allowed_provinces",
        "delivery_windows",
        "payment_methods",
        "contact_phone",
        "contact_address",
        "working_hours",
        "instagram_url",
        "telegram_url",
        "whatsapp_url",
        "bale_url",
        "maps_url",
        "maps_embed_url",
    ):
        if field in settings_payload:
            setattr(settings, field, settings_payload[field])
    settings.theme_palette = LIVE_THEME_PALETTE
    settings.save()


def main() -> None:
    live_settings = read_json("live-settings.json")
    live_categories = read_json("live-categories.json")
    live_products = read_json("live-products.json")

    with transaction.atomic():
        category_count, category_deleted = sync_categories(live_categories)
        product_count, product_deleted = sync_products(live_products)
        sync_settings(live_settings)

    print(
        json.dumps(
            {
                "categories_upserted": category_count,
                "categories_deleted": category_deleted,
                "products_upserted": product_count,
                "products_deleted": product_deleted,
                "theme_palette": LIVE_THEME_PALETTE,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

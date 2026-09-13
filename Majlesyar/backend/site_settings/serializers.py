from rest_framework import serializers

from catalog.models import Category, InternalLink
from catalog.services import get_page_products
from .models import SiteSetting


DEFAULT_INTERNAL_LINKS_BY_PAGE = {
    "/pack/memorial": [
        {"label": "حلوا خرما و خرما گردو", "url": "/halva-khorma"},
        {"label": "تاج گل‌های ترحیم و تسلیت", "url": "/flower/memorial-wreaths"},
        {"label": "فینگر فود", "url": "/food/finger_food"},
        {"label": "ساخت پک اختصاصی", "url": "/builder"},
    ],
}


class SiteSettingSerializer(serializers.ModelSerializer):
    site_logo = serializers.SerializerMethodField()
    site_favicon = serializers.SerializerMethodField()
    site_og_image = serializers.SerializerMethodField()
    event_pages = serializers.SerializerMethodField()

    class Meta:
        model = SiteSetting
        fields = (
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
            "eitaa_url",
            "soroush_url",
            "rubika_url",
            "maps_url",
            "maps_embed_url",
            "site_logo",
            "site_favicon",
            "site_og_image",
            "site_branding",
            "theme_palette",
            "page_seo",
            "event_pages",
            "site_top_notice",
            "homepage_benefits_section",
        )

    def _build_absolute_media_url(self, field) -> str | None:
        if not field:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(field.url)
        return field.url

    def get_site_logo(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_logo)

    def get_site_favicon(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_favicon)

    def get_site_og_image(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_og_image)

    def _absolute_url(self, url: str | None) -> str | None:
        if not url:
            return None
        if url.startswith(("http://", "https://")):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def _product_image_url(self, product) -> str | None:
        payload = getattr(product, "image_variants", None) or {}
        fallback = payload.get("original", {}).get("backup_url") if isinstance(payload.get("original"), dict) else None
        if fallback:
            return self._absolute_url(str(fallback))
        if product.image:
            return self._absolute_url(product.image.url)
        return None

    def _linked_event_page(self, link_url: str, pages_by_route: dict[str, dict]) -> dict | None:
        normalized = self._normalize_path(link_url)
        return pages_by_route.get(normalized)

    @staticmethod
    def _normalize_path(path: str | None) -> str:
        raw = str(path or "").strip()
        if not raw:
            return ""
        normalized = f"/{raw.strip('/')}" if raw.strip("/") else "/"
        return normalized.rstrip("/") or "/"

    def _category_logo_for_slug(self, slug: str | None) -> str | None:
        if not slug:
            return None
        category = Category.objects.filter(slug=slug).only("logo").first()
        if category and category.logo:
            return self._absolute_url(category.logo.url)
        return None

    def _image_for_event_page(self, page: dict | None) -> tuple[str | None, str]:
        if not page:
            return None, ""
        slug = str(page.get("slug") or "").strip()

        try:
            _target, products, _uses_custom_order = get_page_products("event", slug)
        except Exception:
            products = []

        for product in products:
            image_url = self._product_image_url(product)
            if image_url:
                return image_url, product.image_alt or product.image_name or product.name

        category_logo = self._category_logo_for_slug(slug)
        if category_logo:
            return category_logo, str(page.get("name") or "")

        return None, ""

    def _direct_child_links(self, page: dict, event_pages: list[dict]) -> list[dict[str, str]]:
        route_path = self._normalize_path(page.get("route_path") or f"/events/{page.get('slug', '')}")
        if not route_path or route_path == "/":
            return []
        parent_depth = len([part for part in route_path.split("/") if part])
        children: list[dict[str, str]] = []
        for child in event_pages:
            if not isinstance(child, dict) or child is page or child.get("hidden") or child.get("available") is False:
                continue
            child_route = self._normalize_path(child.get("route_path") or f"/events/{child.get('slug', '')}")
            child_depth = len([part for part in child_route.split("/") if part])
            if child_route.startswith(f"{route_path}/") and child_depth == parent_depth + 1:
                children.append({"label": str(child.get("name") or child.get("slug") or ""), "url": child_route})
        return [link for link in children if link["label"] and link["url"]]

    def _managed_internal_links(self, page: dict) -> list[dict]:
        source_path = self._normalize_path(page.get("route_path") or f"/events/{page.get('slug', '')}")
        managed_links = []
        for item in InternalLink.objects.filter(source_path=source_path, is_active=True).order_by("position", "created_at"):
            link = {"label": item.label, "url": item.target_url, "image_alt": item.image_alt or item.label}
            if item.image:
                link["image"] = item.image.url
            managed_links.append(link)
        return managed_links

    def _enrich_internal_links(self, page: dict, event_pages: list[dict], pages_by_route: dict[str, dict]) -> list[dict]:
        links: list[dict] = []
        seen_urls: set[str] = set()
        source_path = self._normalize_path(page.get("route_path") or f"/events/{page.get('slug', '')}")
        raw_links = (
            self._managed_internal_links(page)
            + DEFAULT_INTERNAL_LINKS_BY_PAGE.get(source_path, [])
            + list(page.get("internal_links") or [])
            + self._direct_child_links(page, event_pages)
        )

        for raw_link in raw_links:
            if not isinstance(raw_link, dict):
                continue
            label = str(raw_link.get("label") or "").strip()
            url = self._normalize_path(raw_link.get("url"))
            if not label or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            link = {"label": label, "url": url}

            image = raw_link.get("image")
            image_alt = raw_link.get("image_alt")
            linked_page = self._linked_event_page(url, pages_by_route)
            if not image:
                image, inferred_alt = self._image_for_event_page(linked_page)
                image_alt = image_alt or inferred_alt
            if image:
                link["image"] = self._absolute_url(str(image))
            if image_alt:
                link["image_alt"] = str(image_alt)
            links.append(link)
        return links

    def get_event_pages(self, obj: SiteSetting) -> list[dict]:
        event_pages = [dict(page) for page in (obj.event_pages or []) if isinstance(page, dict)]
        pages_by_route = {
            self._normalize_path(page.get("route_path") or f"/events/{page.get('slug', '')}"): page
            for page in event_pages
        }
        for page in event_pages:
            page["internal_links"] = self._enrich_internal_links(page, event_pages, pages_by_route)
        return event_pages


class SiteSettingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = (
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
            "eitaa_url",
            "soroush_url",
            "rubika_url",
            "maps_url",
            "maps_embed_url",
            "site_logo",
            "site_favicon",
            "site_og_image",
            "site_branding",
            "theme_palette",
            "page_seo",
            "event_pages",
            "site_top_notice",
            "homepage_benefits_section",
        )

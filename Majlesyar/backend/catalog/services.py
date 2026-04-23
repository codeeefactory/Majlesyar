from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from django.db import transaction

from site_settings.models import SiteSetting

from .models import PageProductPlacement, Product


@dataclass(frozen=True)
class PagePreviewTargetDefinition:
    page_type: str
    page_slug: str
    page_title: str
    page_description: str
    route_path: str

    @property
    def page_key(self) -> str:
        if self.page_type == PageProductPlacement.PageType.EVENT:
            return f"event:{self.page_slug}"
        return self.page_type


def get_page_preview_targets() -> list[PagePreviewTargetDefinition]:
    settings = SiteSetting.load()
    targets = [
        PagePreviewTargetDefinition(
            page_type=PageProductPlacement.PageType.HOME,
            page_slug="featured",
            page_title="صفحه اصلی",
            page_description="پیش‌نمایش بخش محصولات ویژه در صفحه اصلی.",
            route_path="/",
        ),
        PagePreviewTargetDefinition(
            page_type=PageProductPlacement.PageType.SHOP,
            page_slug="listing",
            page_title="فروشگاه",
            page_description="ترتیب اصلی نمایش محصولات در صفحه فروشگاه.",
            route_path="/shop",
        ),
    ]

    for event_page in settings.event_pages or []:
        slug = str(event_page.get("slug") or "").strip()
        if not slug:
            continue
        targets.append(
            PagePreviewTargetDefinition(
                page_type=PageProductPlacement.PageType.EVENT,
                page_slug=slug,
                page_title=str(event_page.get("name") or slug),
                page_description=str(event_page.get("description") or ""),
                route_path=f"/events/{slug}",
            )
        )

    return targets


def get_page_preview_target(page_type: str, page_slug: str | None = None) -> PagePreviewTargetDefinition:
    normalized_slug = (page_slug or "").strip()
    for target in get_page_preview_targets():
        if target.page_type == page_type and target.page_slug == normalized_slug:
            return target
    raise ValueError("صفحه‌ی انتخاب‌شده برای چیدمان محصولات معتبر نیست.")


def get_page_product_placements(page_type: str, page_slug: str | None = None):
    normalized_slug = (page_slug or "").strip()
    return PageProductPlacement.objects.select_related("product").prefetch_related(
        "product__categories",
        "product__tags",
    ).filter(
        page_type=page_type,
        page_slug=normalized_slug,
    ).order_by("position", "created_at")


def _get_default_products_for_target(target: PagePreviewTargetDefinition) -> list[Product]:
    queryset = Product.objects.prefetch_related("categories", "tags").all()

    if target.page_type == PageProductPlacement.PageType.HOME:
        return list(queryset.filter(featured=True)[:4])

    if target.page_type == PageProductPlacement.PageType.EVENT:
        return list(queryset.filter(event_types__contains=[target.page_slug]))

    return list(queryset)


def get_page_products(page_type: str, page_slug: str | None = None) -> tuple[PagePreviewTargetDefinition, list[Product], bool]:
    target = get_page_preview_target(page_type, page_slug)
    placements = list(get_page_product_placements(page_type, page_slug))

    if not placements:
        return target, _get_default_products_for_target(target), False

    ordered_products = [placement.product for placement in placements if placement.product]

    if target.page_type == PageProductPlacement.PageType.SHOP:
        placed_ids = {product.id for product in ordered_products}
        remaining_products = [
            product
            for product in _get_default_products_for_target(target)
            if product.id not in placed_ids
        ]
        ordered_products.extend(remaining_products)

    return target, ordered_products, True


@transaction.atomic
def save_page_product_order(
    *,
    page_type: str,
    page_slug: str | None,
    product_ids: Iterable,
    actor=None,
) -> list[PageProductPlacement]:
    target = get_page_preview_target(page_type, page_slug)
    normalized_slug = target.page_slug
    normalized_ids = [str(product_id) for product_id in product_ids]

    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("یک محصول بیش از یک بار در همان صفحه تکرار شده است.")

    products = {
        str(product.id): product
        for product in Product.objects.filter(id__in=normalized_ids)
    }
    missing_ids = [product_id for product_id in normalized_ids if product_id not in products]
    if missing_ids:
        raise ValueError("برخی از محصولات انتخاب‌شده دیگر در سیستم وجود ندارند.")

    existing = {
        str(placement.product_id): placement
        for placement in get_page_product_placements(page_type, normalized_slug)
    }

    PageProductPlacement.objects.filter(
        page_type=page_type,
        page_slug=normalized_slug,
    ).exclude(product_id__in=normalized_ids).delete()

    for index, product_id in enumerate(normalized_ids, start=1):
        placement = existing.get(product_id)
        if placement is None:
            PageProductPlacement.objects.create(
                page_type=page_type,
                page_slug=normalized_slug,
                product=products[product_id],
                position=index,
            )
            continue

        if placement.position != index:
            placement.position = index
            placement.save(update_fields=["position", "updated_at"])

    if actor is not None and getattr(actor, "is_authenticated", False):
        from operations.models import OperationsAuditLog

        OperationsAuditLog.objects.create(
            actor=actor,
            action="page_product_order_saved",
            entity_type="page_product_order",
            entity_id=target.page_key,
            metadata={
                "page_type": page_type,
                "page_slug": normalized_slug,
                "product_ids": normalized_ids,
            },
        )

    return list(get_page_product_placements(page_type, normalized_slug))


def serialize_page_preview_target(target: PagePreviewTargetDefinition) -> dict:
    payload = asdict(target)
    payload["page_key"] = target.page_key
    return payload


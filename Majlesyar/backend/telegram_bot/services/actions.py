from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from catalog.models import Category, Product
from catalog.serializers import ProductSerializer, ProductWriteSerializer
from orders.models import Order
from orders.serializers import OrderSerializer, OrderStatusUpdateSerializer
from site_settings.models import SiteSetting
from site_settings.serializers import SiteSettingSerializer


User = get_user_model()


ORDER_STATUS_FLOW = [
    Order.Status.PENDING,
    Order.Status.CONFIRMED,
    Order.Status.PREPARING,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
]


def resolve_product(identifier: str) -> Product | None:
    cleaned = (identifier or "").strip()
    if not cleaned:
        return None
    product = Product.objects.prefetch_related("categories", "tags").filter(url_slug=cleaned).first()
    if product:
        return product
    try:
        product_uuid = uuid.UUID(cleaned)
    except (TypeError, ValueError):
        return None
    return Product.objects.prefetch_related("categories", "tags").filter(pk=product_uuid).first()


def search_products(query: str = "", *, limit: int = 5) -> list[Product]:
    qs = Product.objects.prefetch_related("categories", "tags").all()
    cleaned = (query or "").strip()
    if cleaned:
        qs = qs.filter(
            Q(name__icontains=cleaned)
            | Q(url_slug__icontains=cleaned)
            | Q(description__icontains=cleaned)
        )
    return list(qs.order_by("-featured", "-updated_at")[:limit])


def serialize_product(product: Product) -> dict[str, Any]:
    return ProductSerializer(product).data


def update_product_flag(identifier: str, *, field: str, value: bool) -> tuple[Product | None, dict[str, Any] | None, dict[str, Any] | None]:
    product = resolve_product(identifier)
    if not product:
        return None, None, None
    previous = {"featured": product.featured, "available": product.available}
    serializer = ProductWriteSerializer(product, data={field: value}, partial=True)
    serializer.is_valid(raise_exception=True)
    updated = serializer.save()
    current = {"featured": updated.featured, "available": updated.available}
    return updated, previous, current


def get_product_stats() -> dict[str, Any]:
    return {
        "total": Product.objects.count(),
        "featured": Product.objects.filter(featured=True).count(),
        "available": Product.objects.filter(available=True).count(),
        "unavailable": Product.objects.filter(available=False).count(),
        "categories": list(Category.objects.values("name", "slug").order_by("name")),
    }


def resolve_order(public_id: str) -> Order | None:
    cleaned = (public_id or "").strip().upper()
    if not cleaned:
        return None
    return Order.objects.prefetch_related("items", "notes").filter(public_id=cleaned).first()


def list_orders(status: str | None = None, *, limit: int = 5) -> list[Order]:
    qs = Order.objects.prefetch_related("items", "notes").all()
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at")[:limit])


def serialize_order(order: Order) -> dict[str, Any]:
    return OrderSerializer(order).data


def next_order_status(order: Order) -> str | None:
    try:
        index = ORDER_STATUS_FLOW.index(order.status)
    except ValueError:
        return None
    if index >= len(ORDER_STATUS_FLOW) - 1:
        return None
    return ORDER_STATUS_FLOW[index + 1]


def update_order_status(public_id: str, status: str) -> tuple[Order | None, dict[str, Any] | None, dict[str, Any] | None]:
    order = resolve_order(public_id)
    if not order:
        return None, None, None
    previous = {"status": order.status}
    serializer = OrderStatusUpdateSerializer(order, data={"status": status}, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    order.refresh_from_db()
    current = {"status": order.status}
    return order, previous, current


def get_order_stats() -> dict[str, Any]:
    today = timezone.localdate()
    return {
        "total": Order.objects.count(),
        "today": Order.objects.filter(created_at__date=today).count(),
        "pending": Order.objects.filter(status=Order.Status.PENDING).count(),
        "confirmed": Order.objects.filter(status=Order.Status.CONFIRMED).count(),
        "preparing": Order.objects.filter(status=Order.Status.PREPARING).count(),
        "shipped": Order.objects.filter(status=Order.Status.SHIPPED).count(),
        "delivered": Order.objects.filter(status=Order.Status.DELIVERED).count(),
    }


def get_settings_snapshot() -> dict[str, Any]:
    return SiteSettingSerializer(SiteSetting.load()).data


def get_dashboard_snapshot() -> dict[str, Any]:
    return {
        "products": get_product_stats(),
        "orders": get_order_stats(),
        "settings": get_settings_snapshot(),
        "recent_orders": [serialize_order(order) for order in list_orders(limit=5)],
        "recent_products": [serialize_product(product) for product in search_products(limit=5)],
        "users": {
            "total": User.objects.count(),
            "staff": User.objects.filter(is_staff=True).count(),
        },
    }

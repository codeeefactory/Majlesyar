from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from orders.models import Order


STATUS_LABELS = {
    Order.Status.PENDING: "در انتظار",
    Order.Status.CONFIRMED: "تایید شده",
    Order.Status.PREPARING: "آماده‌سازی",
    Order.Status.SHIPPED: "ارسال شده",
    Order.Status.DELIVERED: "تحویل شده",
}


def mask_phone(phone: str) -> str:
    cleaned = (phone or "").strip()
    if len(cleaned) < 7:
        return cleaned
    return f"{cleaned[:4]}***{cleaned[-3:]}"


def format_product_summary(product: dict) -> str:
    price = product["price"]
    price_text = "توافقی" if price is None else f"{int(price):,} تومان"
    contents = ", ".join(product["contents"][:5]) if product["contents"] else "ثبت نشده"
    return (
        f"محصول: {product['name']}\n"
        f"شناسه: {product['id']}\n"
        f"اسلاگ: {product['url_slug']}\n"
        f"قیمت: {price_text}\n"
        f"ویژه: {'بله' if product['featured'] else 'خیر'} | موجود: {'بله' if product['available'] else 'خیر'}\n"
        f"محتویات: {contents}"
    )


def format_order_summary(order: dict, *, redact: bool = True) -> str:
    customer = order["customer"]
    phone = mask_phone(customer["phone"]) if redact else customer["phone"]
    created_at = timezone.localtime(datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")))
    return (
        f"سفارش: {order['public_id']}\n"
        f"وضعیت: {STATUS_LABELS.get(order['status'], order['status'])}\n"
        f"مشتری: {customer['name']} | {phone}\n"
        f"مبلغ: {int(order['total']):,} تومان\n"
        f"تحویل: {order['delivery']['date']} / {order['delivery']['window']}\n"
        f"ثبت: {created_at.strftime('%Y-%m-%d %H:%M')}"
    )


def format_help_text() -> str:
    return (
        "دستورات بات مدیریت مجلس‌یار:\n"
        "/start\n"
        "/help\n"
        "/ping\n"
        "/whoami\n"
        "/status\n"
        "/health\n"
        "/dashboard\n"
        "/products [query]\n"
        "/product <slug-or-id>\n"
        "/feature <slug-or-id>\n"
        "/unfeature <slug-or-id>\n"
        "/activate <slug-or-id>\n"
        "/deactivate <slug-or-id>\n"
        "/orders [status]\n"
        "/order <public_id>\n"
        "/orderstatus <public_id> <pending|confirmed|preparing|shipped|delivered>\n"
        "/settings"
    )


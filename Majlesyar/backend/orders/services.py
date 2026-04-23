from __future__ import annotations

import uuid
from datetime import date

from catalog.models import Product

from .models import OrderItem


def build_product_sales_report(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: uuid.UUID | None = None,
) -> dict:
    queryset = OrderItem.objects.select_related("order", "product").filter(product__isnull=False)

    if date_from is not None:
        queryset = queryset.filter(order__created_at__date__gte=date_from)

    if date_to is not None:
        queryset = queryset.filter(order__created_at__date__lte=date_to)

    if product_id is not None:
        queryset = queryset.filter(product_id=product_id)

    rows = []
    total_quantity = 0
    total_revenue = 0
    unique_clients: set[tuple[str, str]] = set()
    selected_product_name = ""

    for item in queryset.order_by("-order__created_at", "-order__delivery_date", "-id"):
        if item.product and not selected_product_name:
            selected_product_name = item.product.name

        line_total = item.quantity * item.price
        total_quantity += item.quantity
        total_revenue += line_total
        unique_clients.add((item.order.customer_phone, item.order.customer_name))

        rows.append(
            {
                "order_public_id": item.order.public_id,
                "order_status": item.order.status,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else item.name,
                "client_name": item.order.customer_name,
                "client_phone": item.order.customer_phone,
                "quantity": item.quantity,
                "unit_price": item.price,
                "line_total": line_total,
                "ordered_at": item.order.created_at,
                "delivery_date": item.order.delivery_date,
            }
        )

    if product_id is not None and not selected_product_name:
        selected_product_name = Product.objects.filter(pk=product_id).values_list("name", flat=True).first() or ""

    return {
        "date_from": date_from,
        "date_to": date_to,
        "product_id": product_id,
        "product_name": selected_product_name,
        "rows_count": len(rows),
        "total_quantity": total_quantity,
        "total_revenue": total_revenue,
        "unique_clients_count": len(unique_clients),
        "rows": rows,
    }

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from orders.models import Order
from telegram_bot.models import TelegramBotState, TelegramOperator
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.formatters import STATUS_LABELS


ORDER_NOTIFICATION_STATE_KEY = "new_order_notifications"


def send_new_order_notifications(client: TelegramApiClient | None = None) -> int:
    if not settings.TELEGRAM_BOT["NOTIFICATIONS_ENABLED"]:
        return 0

    client = client or TelegramApiClient()
    state, _ = TelegramBotState.objects.get_or_create(key=ORDER_NOTIFICATION_STATE_KEY, defaults={"value": {}})
    last_created_at_raw = state.value.get("last_created_at")
    last_created_at = None
    if last_created_at_raw:
        last_created_at = datetime_from_iso(last_created_at_raw)

    qs = Order.objects.order_by("created_at")
    if last_created_at is not None:
        qs = qs.filter(created_at__gt=last_created_at)
    orders = list(qs[:10])
    if not orders:
        return 0

    recipients = TelegramOperator.objects.filter(
        is_active=True,
        notifications_enabled=True,
        telegram_chat_id__isnull=False,
    )
    lines = ["هشدار سفارش‌های جدید:"]
    for order in orders:
        lines.append(
            f"{order.public_id} | {STATUS_LABELS.get(order.status, order.status)} | {order.total:,} تومان"
        )
    text = "\n".join(lines)

    sent = 0
    for operator in recipients:
        client.send_message(operator.telegram_chat_id, text)
        sent += 1

    state.value = {"last_created_at": orders[-1].created_at.isoformat()}
    state.save(update_fields=["value", "updated_at"])
    return sent


def datetime_from_iso(value: str):
    parsed = timezone.datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


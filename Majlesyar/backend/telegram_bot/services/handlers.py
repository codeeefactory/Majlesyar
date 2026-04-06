from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from telegram_bot.models import TelegramBotAuditLog, TelegramConfirmation
from telegram_bot.services import actions
from telegram_bot.services.auth import ResolvedActor, check_access, is_rate_limited
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.formatters import (
    STATUS_LABELS,
    format_help_text,
    format_order_summary,
    format_product_summary,
)


@dataclass
class HandlerResult:
    text: str
    reply_markup: dict[str, Any] | None = None
    audit_status: str = TelegramBotAuditLog.Status.SUCCESS
    action: str = ""
    target_type: str = ""
    target_identifier: str = ""
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


def _confirmation_markup(confirmation: TelegramConfirmation) -> dict[str, Any]:
    return {
        "inline_keyboard": [[
            {"text": "تایید", "callback_data": f"confirm:{confirmation.token}"},
            {"text": "لغو", "callback_data": f"cancel:{confirmation.token}"},
        ]]
    }


def _create_confirmation(
    actor: ResolvedActor,
    *,
    command: str,
    action: str,
    target_type: str,
    target_identifier: str,
    payload: dict[str, Any],
) -> TelegramConfirmation:
    audit_log = TelegramBotAuditLog.objects.create(
        telegram_user_id=actor.telegram_user_id,
        telegram_chat_id=actor.telegram_chat_id,
        operator=actor.operator,
        django_user=actor.django_user,
        command=command,
        action=action,
        target_type=target_type,
        target_identifier=target_identifier,
        metadata={"payload": payload},
        status=TelegramBotAuditLog.Status.PENDING,
    )
    return TelegramConfirmation.create_for_action(
        operator=actor.operator,
        telegram_user_id=actor.telegram_user_id,
        telegram_chat_id=actor.telegram_chat_id,
        action=action,
        command=command,
        target_type=target_type,
        target_identifier=target_identifier,
        payload=payload,
        audit_log=audit_log,
    )


def handle_command(actor: ResolvedActor, text: str) -> HandlerResult:
    allowed, reason = check_access(actor)
    if not allowed:
        return HandlerResult(text=reason, audit_status=TelegramBotAuditLog.Status.DENIED, action="access_denied")
    if is_rate_limited(actor):
        return HandlerResult(
            text="تعداد درخواست‌های شما در یک دقیقه اخیر زیاد بوده است. کمی بعد دوباره تلاش کنید.",
            audit_status=TelegramBotAuditLog.Status.DENIED,
            action="rate_limited",
        )

    parts = (text or "").strip().split()
    if not parts:
        return HandlerResult(text="پیام خالی دریافت شد.", audit_status=TelegramBotAuditLog.Status.IGNORED)
    command = parts[0].split("@", 1)[0].lower()
    args = parts[1:]

    if command in {"/start", "/help"}:
        return HandlerResult(text=format_help_text(), action="help")
    if command == "/ping":
        return HandlerResult(text=f"pong {timezone.now().isoformat()}", action="ping")
    if command == "/whoami":
        mapped_user = actor.django_user.username if actor.django_user else "نگاشت نشده"
        return HandlerResult(
            text=(
                f"Telegram: {actor.display_name}\n"
                f"user_id: {actor.telegram_user_id}\n"
                f"chat_id: {actor.telegram_chat_id}\n"
                f"Django: {mapped_user}"
            ),
            action="whoami",
        )
    if command == "/health":
        dashboard = actions.get_dashboard_snapshot()
        return HandlerResult(
            text=(
                "وضعیت سامانه:\n"
                f"محصولات: {dashboard['products']['total']}\n"
                f"سفارش‌ها: {dashboard['orders']['total']}\n"
                f"کاربران: {dashboard['users']['total']}"
            ),
            action="health",
        )
    if command == "/status":
        stats = actions.get_order_stats()
        return HandlerResult(
            text=(
                "خلاصه عملیات:\n"
                f"امروز: {stats['today']}\n"
                f"در انتظار: {stats['pending']}\n"
                f"در آماده‌سازی: {stats['preparing']}\n"
                f"ارسال شده: {stats['shipped']}"
            ),
            action="status",
        )
    if command == "/dashboard":
        dashboard = actions.get_dashboard_snapshot()
        return HandlerResult(
            text=(
                "داشبورد مجلس‌یار:\n"
                f"محصولات: {dashboard['products']['total']} | ویژه: {dashboard['products']['featured']} | ناموجود: {dashboard['products']['unavailable']}\n"
                f"سفارش‌ها: {dashboard['orders']['total']} | امروز: {dashboard['orders']['today']} | در انتظار: {dashboard['orders']['pending']}\n"
                f"کاربران: {dashboard['users']['total']} | staff: {dashboard['users']['staff']}\n"
                f"استان‌های فعال: {', '.join(dashboard['settings']['allowed_provinces']) or 'ثبت نشده'}"
            ),
            action="dashboard",
            metadata=dashboard,
        )
    if command == "/products":
        query = " ".join(args).strip()
        products = actions.search_products(query, limit=5)
        if not products:
            return HandlerResult(text="محصولی پیدا نشد.", action="product_search", target_identifier=query)
        lines = ["محصولات:"]
        for product in products:
            lines.append(f"- {product.name} | {product.url_slug} | {'ویژه' if product.featured else 'عادی'}")
        return HandlerResult(text="\n".join(lines), action="product_search", target_identifier=query)
    if command == "/product":
        if not args:
            return HandlerResult(text="استفاده: /product <slug-or-id>", audit_status=TelegramBotAuditLog.Status.IGNORED)
        product = actions.resolve_product(args[0])
        if not product:
            return HandlerResult(
                text="محصول پیدا نشد.",
                action="product_detail",
                target_type="product",
                target_identifier=args[0],
                audit_status=TelegramBotAuditLog.Status.FAILED,
            )
        serialized = actions.serialize_product(product)
        feature_confirmation = _create_confirmation(
            actor,
            command="/product",
            action="set_product_featured" if not product.featured else "unset_product_featured",
            target_type="product",
            target_identifier=str(product.id),
            payload={"identifier": str(product.id), "field": "featured", "value": not product.featured},
        )
        availability_confirmation = _create_confirmation(
            actor,
            command="/product",
            action="set_product_available" if not product.available else "set_product_unavailable",
            target_type="product",
            target_identifier=str(product.id),
            payload={"identifier": str(product.id), "field": "available", "value": not product.available},
        )
        return HandlerResult(
            text=format_product_summary(serialized),
            reply_markup={
                "inline_keyboard": [[
                    {
                        "text": "حذف از ویژه" if product.featured else "ویژه‌کردن",
                        "callback_data": f"confirm:{feature_confirmation.token}",
                    },
                    {
                        "text": "غیرفعال‌کردن" if product.available else "فعال‌کردن",
                        "callback_data": f"confirm:{availability_confirmation.token}",
                    },
                ]]
            },
            action="product_detail",
            target_type="product",
            target_identifier=args[0],
        )
    if command in {"/feature", "/unfeature", "/activate", "/deactivate"}:
        if not args:
            return HandlerResult(text=f"استفاده: {command} <slug-or-id>", audit_status=TelegramBotAuditLog.Status.IGNORED)
        field = "featured" if command in {"/feature", "/unfeature"} else "available"
        value = command in {"/feature", "/activate"}
        confirmation = _create_confirmation(
            actor,
            command=command,
            action=f"{'set' if value else 'unset'}_{field}",
            target_type="product",
            target_identifier=args[0],
            payload={"identifier": args[0], "field": field, "value": value},
        )
        return HandlerResult(
            text=f"تایید تغییر وضعیت محصول:\n{command} {args[0]}",
            reply_markup=_confirmation_markup(confirmation),
            action=f"{'set' if value else 'unset'}_{field}",
            target_type="product",
            target_identifier=args[0],
            audit_status=TelegramBotAuditLog.Status.PENDING,
        )
    if command == "/orders":
        status_filter = args[0] if args else None
        orders = actions.list_orders(status_filter, limit=5)
        if not orders:
            return HandlerResult(text="سفارشی پیدا نشد.", action="order_list", target_identifier=status_filter or "")
        lines = ["سفارش‌ها:"]
        for order in orders:
            lines.append(format_order_summary(actions.serialize_order(order)))
            lines.append("")
        return HandlerResult(text="\n".join(lines).strip(), action="order_list", target_identifier=status_filter or "")
    if command == "/order":
        if not args:
            return HandlerResult(text="استفاده: /order <public_id>", audit_status=TelegramBotAuditLog.Status.IGNORED)
        order = actions.resolve_order(args[0])
        if not order:
            return HandlerResult(
                text="سفارش پیدا نشد.",
                action="order_detail",
                target_type="order",
                target_identifier=args[0],
                audit_status=TelegramBotAuditLog.Status.FAILED,
            )
        serialized = actions.serialize_order(order)
        reply_markup = None
        next_status = actions.next_order_status(order)
        if next_status:
            confirmation = _create_confirmation(
                actor,
                command="/order",
                action="set_order_status",
                target_type="order",
                target_identifier=order.public_id,
                payload={"public_id": order.public_id, "status": next_status},
            )
            reply_markup = {
                "inline_keyboard": [[
                    {
                        "text": f"تغییر به {STATUS_LABELS.get(next_status, next_status)}",
                        "callback_data": f"confirm:{confirmation.token}",
                    }
                ]]
            }
        return HandlerResult(
            text=format_order_summary(serialized, redact=False),
            reply_markup=reply_markup,
            action="order_detail",
            target_type="order",
            target_identifier=args[0],
        )
    if command == "/orderstatus":
        if len(args) != 2:
            return HandlerResult(
                text="استفاده: /orderstatus <public_id> <pending|confirmed|preparing|shipped|delivered>",
                audit_status=TelegramBotAuditLog.Status.IGNORED,
            )
        confirmation = _create_confirmation(
            actor,
            command=command,
            action="set_order_status",
            target_type="order",
            target_identifier=args[0],
            payload={"public_id": args[0], "status": args[1]},
        )
        return HandlerResult(
            text=f"تایید تغییر وضعیت سفارش {args[0]} به {args[1]}",
            reply_markup=_confirmation_markup(confirmation),
            action="set_order_status",
            target_type="order",
            target_identifier=args[0],
            audit_status=TelegramBotAuditLog.Status.PENDING,
        )
    if command == "/settings":
        settings_snapshot = actions.get_settings_snapshot()
        return HandlerResult(
            text=(
                "تنظیمات سایت:\n"
                f"حداقل سفارش: {settings_snapshot['min_order_qty']}\n"
                f"زمان آماده‌سازی: {settings_snapshot['lead_time_hours']} ساعت\n"
                f"استان‌های فعال: {', '.join(settings_snapshot['allowed_provinces']) or 'ثبت نشده'}\n"
                f"تلگرام: {settings_snapshot['telegram_url'] or 'ثبت نشده'}"
            ),
            action="settings_snapshot",
        )
    return HandlerResult(
        text="دستور شناخته نشد. /help را اجرا کنید.",
        audit_status=TelegramBotAuditLog.Status.IGNORED,
        action="unknown_command",
    )


def _execute_confirmation(confirmation: TelegramConfirmation) -> HandlerResult:
    payload = confirmation.payload
    if confirmation.action in {
        "set_featured",
        "unset_featured",
        "set_available",
        "unset_available",
        "set_product_featured",
        "unset_product_featured",
        "set_product_available",
        "set_product_unavailable",
    }:
        product, previous, current = actions.update_product_flag(
            payload["identifier"],
            field=payload["field"],
            value=bool(payload["value"]),
        )
        if not product:
            return HandlerResult(
                text="محصول برای اجرای این تغییر پیدا نشد.",
                audit_status=TelegramBotAuditLog.Status.FAILED,
                action=confirmation.action,
                target_type="product",
                target_identifier=confirmation.target_identifier,
            )
        return HandlerResult(
            text=f"محصول {product.name} به‌روزرسانی شد.",
            action=confirmation.action,
            target_type="product",
            target_identifier=str(product.id),
            previous_state=previous,
            new_state=current,
        )
    if confirmation.action == "set_order_status":
        order, previous, current = actions.update_order_status(
            payload["public_id"],
            payload["status"],
        )
        if not order:
            return HandlerResult(
                text="سفارش برای اجرای این تغییر پیدا نشد.",
                audit_status=TelegramBotAuditLog.Status.FAILED,
                action=confirmation.action,
                target_type="order",
                target_identifier=confirmation.target_identifier,
            )
        return HandlerResult(
            text=f"وضعیت سفارش {order.public_id} به {STATUS_LABELS.get(order.status, order.status)} تغییر کرد.",
            action=confirmation.action,
            target_type="order",
            target_identifier=order.public_id,
            previous_state=previous,
            new_state=current,
        )
    return HandlerResult(
        text="نوع عملیات تاییدی پشتیبانی نمی‌شود.",
        audit_status=TelegramBotAuditLog.Status.FAILED,
        action=confirmation.action,
    )


def handle_callback(actor: ResolvedActor, callback_query: dict, client: TelegramApiClient) -> HandlerResult:
    allowed, reason = check_access(actor)
    if not allowed:
        client.answer_callback_query(callback_query["id"], reason)
        return HandlerResult(text=reason, audit_status=TelegramBotAuditLog.Status.DENIED, action="access_denied")

    data = callback_query.get("data", "")
    if ":" not in data:
        client.answer_callback_query(callback_query["id"], "درخواست نامعتبر است.")
        return HandlerResult(text="درخواست نامعتبر است.", audit_status=TelegramBotAuditLog.Status.IGNORED)
    verb, token = data.split(":", 1)
    confirmation = TelegramConfirmation.objects.filter(token=token).select_related("audit_log").first()
    if not confirmation:
        client.answer_callback_query(callback_query["id"], "تاییدیه پیدا نشد.")
        return HandlerResult(text="تاییدیه پیدا نشد.", audit_status=TelegramBotAuditLog.Status.FAILED, action=verb)
    if confirmation.telegram_user_id != actor.telegram_user_id or confirmation.telegram_chat_id != actor.telegram_chat_id:
        client.answer_callback_query(callback_query["id"], "این تاییدیه برای شما نیست.")
        return HandlerResult(text="این تاییدیه برای شما نیست.", audit_status=TelegramBotAuditLog.Status.DENIED, action=verb)
    if not confirmation.is_active:
        client.answer_callback_query(callback_query["id"], "این تاییدیه منقضی یا مصرف شده است.")
        return HandlerResult(text="این تاییدیه منقضی یا مصرف شده است.", audit_status=TelegramBotAuditLog.Status.FAILED, action=verb)

    message = callback_query.get("message") or {}
    if message.get("message_id"):
        client.edit_message_reply_markup(message["chat"]["id"], message["message_id"])

    if verb == "cancel":
        confirmation.mark_cancelled()
        if confirmation.audit_log:
            confirmation.audit_log.status = TelegramBotAuditLog.Status.IGNORED
            confirmation.audit_log.error_message = "Cancelled by operator."
            confirmation.audit_log.save(update_fields=["status", "error_message"])
        client.answer_callback_query(callback_query["id"], "لغو شد.")
        return HandlerResult(
            text="عملیات لغو شد.",
            audit_status=TelegramBotAuditLog.Status.IGNORED,
            action=confirmation.action,
            target_type=confirmation.target_type,
            target_identifier=confirmation.target_identifier,
        )

    if verb != "confirm":
        client.answer_callback_query(callback_query["id"], "درخواست نامعتبر است.")
        return HandlerResult(text="درخواست نامعتبر است.", audit_status=TelegramBotAuditLog.Status.IGNORED, action=verb)

    with transaction.atomic():
        confirmation.mark_consumed()
        result = _execute_confirmation(confirmation)
        if confirmation.audit_log:
            confirmation.audit_log.status = result.audit_status
            confirmation.audit_log.previous_state = result.previous_state
            confirmation.audit_log.new_state = result.new_state
            confirmation.audit_log.error_message = "" if result.audit_status == TelegramBotAuditLog.Status.SUCCESS else result.text
            confirmation.audit_log.save(update_fields=["status", "previous_state", "new_state", "error_message"])
    client.answer_callback_query(callback_query["id"], "انجام شد." if result.audit_status == TelegramBotAuditLog.Status.SUCCESS else "خطا")
    return result


def persist_audit(actor: ResolvedActor | None, command: str, result: HandlerResult) -> TelegramBotAuditLog:
    return TelegramBotAuditLog.objects.create(
        telegram_user_id=actor.telegram_user_id if actor else None,
        telegram_chat_id=actor.telegram_chat_id if actor else None,
        operator=actor.operator if actor else None,
        django_user=actor.django_user if actor else None,
        command=command,
        action=result.action,
        target_type=result.target_type,
        target_identifier=result.target_identifier,
        previous_state=result.previous_state,
        new_state=result.new_state,
        metadata=result.metadata or {},
        status=result.audit_status,
        error_message="" if result.audit_status == TelegramBotAuditLog.Status.SUCCESS else result.text,
    )


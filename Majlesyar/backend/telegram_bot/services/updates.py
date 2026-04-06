from __future__ import annotations

from django.db import IntegrityError, transaction

from telegram_bot.models import TelegramUpdateReceipt
from telegram_bot.services.auth import get_actor_from_update
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.handlers import handle_callback, handle_command, persist_audit


def process_update(update: dict, *, source: str, client: TelegramApiClient | None = None) -> bool:
    client = client or TelegramApiClient()
    update_id = update.get("update_id")
    if update_id is None:
        return False

    try:
        with transaction.atomic():
            receipt, created = TelegramUpdateReceipt.objects.get_or_create(
                update_id=update_id,
                defaults={
                    "source": source,
                    "payload": update,
                },
            )
    except IntegrityError:
        return False
    if not created:
        return False

    actor = get_actor_from_update(update)
    try:
        if update.get("callback_query"):
            callback_query = update["callback_query"]
            result = handle_callback(actor, callback_query, client) if actor else None
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            if result and chat_id:
                client.send_message(chat_id, result.text)
                persist_audit(actor, "callback_query", result)
        elif update.get("message", {}).get("text"):
            message = update["message"]
            result = handle_command(actor, message["text"]) if actor else None
            if result:
                client.send_message(message["chat"]["id"], result.text, reply_markup=result.reply_markup)
                if result.audit_status != "pending":
                    persist_audit(actor, message["text"].split()[0], result)
        else:
            receipt.status = TelegramUpdateReceipt.Status.IGNORED
            receipt.save(update_fields=["status"])
            return True
    except Exception as exc:
        receipt.status = TelegramUpdateReceipt.Status.FAILED
        receipt.error_message = str(exc)
        receipt.save(update_fields=["status", "error_message"])
        if actor:
            client.send_message(actor.telegram_chat_id, "اجرای این درخواست با خطا مواجه شد.")
        return False

    receipt.status = TelegramUpdateReceipt.Status.PROCESSED
    receipt.save(update_fields=["status"])
    return True

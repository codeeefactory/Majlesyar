from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from telegram_bot.models import TelegramBotAuditLog, TelegramOperator


@dataclass
class ResolvedActor:
    telegram_user_id: int
    telegram_chat_id: int
    username: str
    first_name: str
    last_name: str
    operator: TelegramOperator

    @property
    def django_user(self):
        return self.operator.django_user

    @property
    def display_name(self) -> str:
        return self.operator.display_name


def get_actor_from_update(update: dict) -> ResolvedActor | None:
    message = update.get("message") or {}
    callback_query = update.get("callback_query") or {}
    if callback_query:
        message = callback_query.get("message") or {}
    actor_data = callback_query.get("from") or message.get("from")
    chat_data = message.get("chat") or {}
    if not actor_data or not chat_data:
        return None

    operator, _ = TelegramOperator.objects.update_or_create(
        telegram_user_id=int(actor_data["id"]),
        defaults={
            "telegram_chat_id": int(chat_data["id"]),
            "username": actor_data.get("username", "") or "",
            "first_name": actor_data.get("first_name", "") or "",
            "last_name": actor_data.get("last_name", "") or "",
            "last_seen_at": timezone.now(),
        },
    )
    return ResolvedActor(
        telegram_user_id=int(actor_data["id"]),
        telegram_chat_id=int(chat_data["id"]),
        username=actor_data.get("username", "") or "",
        first_name=actor_data.get("first_name", "") or "",
        last_name=actor_data.get("last_name", "") or "",
        operator=operator,
    )


def check_access(actor: ResolvedActor) -> tuple[bool, str]:
    bot_settings = settings.TELEGRAM_BOT
    if not actor.operator.is_active:
        return False, "حساب تلگرام شما برای بات غیرفعال شده است."

    allowed_user_ids = set(bot_settings["ALLOWED_USER_IDS"])
    if allowed_user_ids and actor.telegram_user_id not in allowed_user_ids:
        return False, "شما در فهرست مجاز این بات نیستید."

    allowed_chat_ids = set(bot_settings["ALLOWED_CHAT_IDS"])
    if allowed_chat_ids and actor.telegram_chat_id not in allowed_chat_ids:
        return False, "این چت برای مدیریت مجاز نیست."

    if bot_settings["ADMIN_ONLY"] and actor.django_user and not actor.django_user.is_staff:
        return False, "کاربر نگاشت‌شده شما دسترسی staff ندارد."

    return True, ""


def is_rate_limited(actor: ResolvedActor) -> bool:
    rate_limit = settings.TELEGRAM_BOT["RATE_LIMIT_PER_MINUTE"]
    if rate_limit <= 0:
        return False
    since = timezone.now() - timezone.timedelta(minutes=1)
    recent_count = TelegramBotAuditLog.objects.filter(
        telegram_user_id=actor.telegram_user_id,
        created_at__gte=since,
    ).count()
    return recent_count >= rate_limit

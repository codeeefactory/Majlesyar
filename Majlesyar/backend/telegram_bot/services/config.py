from __future__ import annotations

from django.conf import settings


def get_bot_settings() -> dict:
    return settings.TELEGRAM_BOT


def bot_enabled() -> bool:
    current = get_bot_settings()
    return bool(current["ENABLED"] and current["TOKEN"])


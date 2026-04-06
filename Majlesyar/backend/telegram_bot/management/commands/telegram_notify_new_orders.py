from __future__ import annotations

from django.core.management.base import BaseCommand

from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.notifications import send_new_order_notifications


class Command(BaseCommand):
    help = "Send Telegram notifications for new orders to subscribed operators."

    def handle(self, *args, **options):
        sent = send_new_order_notifications(TelegramApiClient())
        self.stdout.write(self.style.SUCCESS(f"Notifications sent: {sent}"))


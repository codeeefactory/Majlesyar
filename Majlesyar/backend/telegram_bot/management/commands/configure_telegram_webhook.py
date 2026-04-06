from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.config import bot_enabled


class Command(BaseCommand):
    help = "Configure or remove the Telegram webhook for Majlesyar."

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true")

    def handle(self, *args, **options):
        if not bot_enabled():
            raise CommandError("Telegram bot is disabled or TELEGRAM_BOT_TOKEN is missing.")

        client = TelegramApiClient()
        if options["delete"]:
            result = client.delete_webhook()
            self.stdout.write(self.style.SUCCESS(f"Webhook deleted: {result}"))
            return

        base_url = settings.TELEGRAM_BOT["BASE_URL"]
        if not base_url:
            raise CommandError("TELEGRAM_BOT_BASE_URL is required to configure the webhook.")

        webhook_url = f"{base_url}/{settings.TELEGRAM_BOT['WEBHOOK_PATH'].strip('/')}"
        result = client.set_webhook(webhook_url, settings.TELEGRAM_BOT["WEBHOOK_SECRET"] or None)
        self.stdout.write(self.style.SUCCESS(f"Webhook configured: {result}"))


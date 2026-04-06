from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegram_bot.models import TelegramUpdateReceipt
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.config import bot_enabled
from telegram_bot.services.updates import process_update


class Command(BaseCommand):
    help = "Run the Majlesyar Telegram bot in long-polling mode."

    def add_arguments(self, parser):
        parser.add_argument("--poll-timeout", type=int, default=30)
        parser.add_argument("--sleep-seconds", type=int, default=2)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        if not bot_enabled():
            raise CommandError("Telegram bot is disabled or TELEGRAM_BOT_TOKEN is missing.")

        if settings.TELEGRAM_BOT["USE_WEBHOOK"] and not options["once"]:
            self.stdout.write(self.style.WARNING("TELEGRAM_BOT_USE_WEBHOOK=1, but polling was requested."))

        client = TelegramApiClient()
        offset = TelegramUpdateReceipt.objects.order_by("-update_id").values_list("update_id", flat=True).first()
        if offset is not None:
            offset += 1

        while True:
            updates = client.get_updates(offset=offset, timeout=options["poll_timeout"])
            for update in updates:
                process_update(update, source="polling", client=client)
                offset = int(update["update_id"]) + 1
            if options["once"]:
                break
            time.sleep(options["sleep_seconds"])


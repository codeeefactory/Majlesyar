from __future__ import annotations

import json

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.config import bot_enabled
from telegram_bot.services.updates import process_update


class TelegramWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not bot_enabled():
            raise Http404

        expected_secret = settings.TELEGRAM_BOT["WEBHOOK_SECRET"]
        if expected_secret:
            received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if received_secret != expected_secret:
                return Response({"detail": "Invalid webhook secret."}, status=status.HTTP_403_FORBIDDEN)

        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON payload."}, status=status.HTTP_400_BAD_REQUEST)

        process_update(payload, source="webhook", client=TelegramApiClient())
        return Response({"ok": True})


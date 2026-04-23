from __future__ import annotations

import json

from django.conf import settings
from django.http import Http404
from django.db.models import Q
from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.permissions import IsStaffUser
from telegram_bot.models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.config import bot_enabled
from telegram_bot.services.updates import process_update
from .serializers import (
    TelegramBotAuditLogSerializer,
    TelegramBotStateSerializer,
    TelegramConfirmationSerializer,
    TelegramOperatorSerializer,
    TelegramOperatorWriteSerializer,
    TelegramUpdateReceiptSerializer,
)


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


class TelegramOperatorListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        queryset = TelegramOperator.objects.select_related("django_user").all()
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(telegram_user_id__icontains=search)
                | Q(django_user__username__icontains=search)
            )
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() == "true")
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TelegramOperatorWriteSerializer
        return TelegramOperatorSerializer


class TelegramOperatorDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    queryset = TelegramOperator.objects.select_related("django_user").all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return TelegramOperatorWriteSerializer
        return TelegramOperatorSerializer


class TelegramBotAuditLogListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = TelegramBotAuditLogSerializer

    def get_queryset(self):
        queryset = TelegramBotAuditLog.objects.select_related("operator", "django_user").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        command = self.request.query_params.get("command")
        if command:
            queryset = queryset.filter(command__icontains=command)
        return queryset


class TelegramConfirmationListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = TelegramConfirmationSerializer

    def get_queryset(self):
        queryset = TelegramConfirmation.objects.select_related("operator").all()
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)
        return queryset


class TelegramUpdateReceiptListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = TelegramUpdateReceiptSerializer

    def get_queryset(self):
        queryset = TelegramUpdateReceipt.objects.all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        source = self.request.query_params.get("source")
        if source:
            queryset = queryset.filter(source=source)
        return queryset


class TelegramBotStateListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    queryset = TelegramBotState.objects.all()
    serializer_class = TelegramBotStateSerializer


class TelegramBotStateDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    queryset = TelegramBotState.objects.all()
    serializer_class = TelegramBotStateSerializer

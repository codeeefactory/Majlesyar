from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)


User = get_user_model()


class TelegramOperatorSerializer(serializers.ModelSerializer):
    django_username = serializers.CharField(source="django_user.username", read_only=True)

    class Meta:
        model = TelegramOperator
        fields = (
            "id",
            "telegram_user_id",
            "telegram_chat_id",
            "username",
            "first_name",
            "last_name",
            "display_name",
            "django_user",
            "django_username",
            "is_active",
            "notifications_enabled",
            "last_seen_at",
            "created_at",
            "updated_at",
        )


class TelegramOperatorWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramOperator
        fields = (
            "id",
            "telegram_user_id",
            "telegram_chat_id",
            "username",
            "first_name",
            "last_name",
            "django_user",
            "is_active",
            "notifications_enabled",
        )
        read_only_fields = ("id",)


class TelegramBotAuditLogSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    django_username = serializers.CharField(source="django_user.username", read_only=True)

    class Meta:
        model = TelegramBotAuditLog
        fields = (
            "id",
            "telegram_user_id",
            "telegram_chat_id",
            "operator_name",
            "django_username",
            "command",
            "action",
            "target_type",
            "target_identifier",
            "status",
            "error_message",
            "metadata",
            "created_at",
        )


class TelegramConfirmationSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)

    class Meta:
        model = TelegramConfirmation
        fields = (
            "id",
            "token",
            "operator_name",
            "telegram_user_id",
            "telegram_chat_id",
            "action",
            "command",
            "target_type",
            "target_identifier",
            "payload",
            "created_at",
            "expires_at",
            "consumed_at",
            "cancelled_at",
        )


class TelegramUpdateReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUpdateReceipt
        fields = (
            "id",
            "update_id",
            "source",
            "status",
            "error_message",
            "processed_at",
        )


class TelegramBotStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramBotState
        fields = ("id", "key", "value", "updated_at")


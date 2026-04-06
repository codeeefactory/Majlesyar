from django.contrib import admin

from .models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)


@admin.register(TelegramOperator)
class TelegramOperatorAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_user_id",
        "username",
        "django_user",
        "is_active",
        "notifications_enabled",
        "last_seen_at",
    )
    list_filter = ("is_active", "notifications_enabled")
    search_fields = ("telegram_user_id", "username", "first_name", "last_name", "django_user__username")


@admin.register(TelegramBotAuditLog)
class TelegramBotAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "command", "action", "target_type", "target_identifier", "status")
    list_filter = ("status", "command", "action", "target_type")
    search_fields = ("target_identifier", "error_message", "telegram_user_id")
    readonly_fields = ("created_at",)


@admin.register(TelegramConfirmation)
class TelegramConfirmationAdmin(admin.ModelAdmin):
    list_display = ("action", "target_identifier", "telegram_user_id", "expires_at", "consumed_at", "cancelled_at")
    list_filter = ("action", "target_type")
    search_fields = ("target_identifier", "telegram_user_id", "telegram_chat_id")


@admin.register(TelegramUpdateReceipt)
class TelegramUpdateReceiptAdmin(admin.ModelAdmin):
    list_display = ("update_id", "source", "status", "processed_at")
    list_filter = ("source", "status")
    search_fields = ("update_id", "error_message")
    readonly_fields = ("processed_at",)


@admin.register(TelegramBotState)
class TelegramBotStateAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key",)

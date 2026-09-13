from django.contrib import admin

from config.admin_mixins import PersianAdminFormMixin

from .models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)


@admin.register(TelegramOperator)
class TelegramOperatorAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = (
        "telegram_user_id",
        "username",
        "django_user",
        "is_active",
        "notifications_enabled",
        "last_seen_at",
    )
    list_filter = ()
    search_fields = ("telegram_user_id", "username", "first_name", "last_name", "django_user__username")
    readonly_fields = ("created_at", "updated_at", "last_seen_at")
    fieldsets = (
        (
            "مشخصات اپراتور تلگرام",
            {
                "description": "راهنما: شناسه عددی تلگرام را دقیق وارد کنید. اگر مطمئن نیستید، مقدار را از لاگ ربات کپی کنید.",
                "fields": ("telegram_user_id", "telegram_chat_id", "username", "first_name", "last_name", "django_user"),
            },
        ),
        (
            "دسترسی و اعلان‌ها",
            {
                "description": "نکته: فقط اپراتورهای فعال می‌توانند از ربات استفاده کنند. اعلان‌ها را برای افراد غیرمسئول خاموش کنید.",
                "fields": ("is_active", "notifications_enabled", "last_seen_at", "created_at", "updated_at"),
            },
        ),
    )


@admin.register(TelegramBotAuditLog)
class TelegramBotAuditLogAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("created_at", "command", "action", "target_type", "target_identifier", "status")
    list_filter = ()
    search_fields = ("target_identifier", "error_message", "telegram_user_id")
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "گزارش عملیات ربات",
            {
                "description": "راهنما: این بخش برای بررسی خطاها و کارهای انجام‌شده توسط ربات است. معمولا نیازی به ویرایش دستی ندارد.",
                "fields": ("operator", "django_user", "telegram_user_id", "telegram_chat_id", "command", "action", "status"),
            },
        ),
        (
            "هدف و جزئیات فنی",
            {
                "description": "نکته: شناسه هدف، وضعیت قبل/بعد و متن خطا برای عیب‌یابی نگهداری می‌شود.",
                "fields": ("target_type", "target_identifier", "previous_state", "new_state", "metadata", "error_message", "created_at"),
            },
        ),
    )


@admin.register(TelegramConfirmation)
class TelegramConfirmationAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("action", "target_identifier", "telegram_user_id", "expires_at", "consumed_at", "cancelled_at")
    list_filter = ()
    search_fields = ("target_identifier", "telegram_user_id", "telegram_chat_id")
    readonly_fields = ("token", "created_at", "consumed_at", "cancelled_at")
    fieldsets = (
        (
            "تایید عملیات حساس",
            {
                "description": "راهنما: این رکورد برای تایید کارهای حساس ربات ساخته می‌شود. توکن و زمان‌ها را دستی تغییر ندهید.",
                "fields": ("token", "operator", "action", "command", "target_type", "target_identifier", "payload"),
            },
        ),
        (
            "زمان و وضعیت",
            {
                "description": "نکته: اگر زمان انقضا گذشته باشد، تایید دیگر معتبر نیست.",
                "fields": ("telegram_user_id", "telegram_chat_id", "audit_log", "created_at", "expires_at", "consumed_at", "cancelled_at"),
            },
        ),
    )


@admin.register(TelegramUpdateReceipt)
class TelegramUpdateReceiptAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("update_id", "source", "status", "processed_at")
    list_filter = ()
    search_fields = ("update_id", "error_message")
    readonly_fields = ("processed_at",)
    fieldsets = (
        (
            "دریافت پیام از تلگرام",
            {
                "description": "راهنما: هر پیام دریافتی از تلگرام اینجا ثبت می‌شود تا پیام تکراری دوباره پردازش نشود.",
                "fields": ("update_id", "source", "status", "payload", "error_message", "processed_at"),
            },
        ),
    )


@admin.register(TelegramBotState)
class TelegramBotStateAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "وضعیت داخلی ربات",
            {
                "description": "راهنما: این مقادیر برای حافظه داخلی ربات هستند. فقط وقتی تغییر دهید که ساختار JSON را می‌دانید.",
                "fields": ("key", "value", "updated_at"),
            },
        ),
    )

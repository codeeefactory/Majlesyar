from django.contrib import admin

from config.admin_mixins import PersianAdminFormMixin
from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("contact_phone", "min_order_qty", "lead_time_hours", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "اطلاعات تماس و شبکه‌های اجتماعی",
            {
                "fields": (
                    "contact_phone",
                    "contact_address",
                    "working_hours",
                    "instagram_url",
                    "telegram_url",
                    "whatsapp_url",
                    "bale_url",
                    "maps_url",
                    "maps_embed_url",
                ),
            },
        ),
        (
            "قوانین سفارش",
            {
                "fields": ("min_order_qty", "lead_time_hours"),
            },
        ),
        (
            "تنظیمات ارسال",
            {
                "fields": ("allowed_provinces", "delivery_windows"),
            },
        ),
        (
            "تنظیمات پرداخت",
            {
                "fields": ("payment_methods", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        if SiteSetting.objects.exists():
            return False
        return super().has_add_permission(request)

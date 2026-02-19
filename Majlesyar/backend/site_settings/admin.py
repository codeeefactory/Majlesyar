from django.contrib import admin

from config.admin_mixins import PersianAdminFormMixin
from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("min_order_qty", "lead_time_hours", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "قوانین سفارش",
            {
                "description": "راهنما: حداقل تعداد سفارش و حداقل زمان آماده سازی را مشخص کنید.",
                "fields": ("min_order_qty", "lead_time_hours"),
            },
        ),
        (
            "تنظیمات ارسال",
            {
                "description": "راهنما: مقادیر را با فرمت JSON معتبر وارد کنید.",
                "fields": ("allowed_provinces", "delivery_windows"),
            },
        ),
        (
            "تنظیمات پرداخت",
            {
                "description": "راهنما: روش های پرداخت را همراه با وضعیت فعال/غیرفعال ثبت کنید.",
                "fields": ("payment_methods", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        if SiteSetting.objects.exists():
            return False
        return super().has_add_permission(request)

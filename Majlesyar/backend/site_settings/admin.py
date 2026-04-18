from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from config.admin_mixins import PersianAdminFormMixin

from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("site_name_display", "contact_phone", "min_order_qty", "lead_time_hours", "updated_at")
    readonly_fields = (
        "site_logo_preview",
        "site_favicon_preview",
        "site_og_image_preview",
        "updated_at",
    )
    formfield_overrides = {
        models.JSONField: {
            "widget": forms.Textarea(
                attrs={
                    "rows": 14,
                    "dir": "ltr",
                    "style": "width: 100%; font-family: Consolas, 'Courier New', monospace;",
                }
            ),
        },
    }
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
            "هویت برند، لوگو و سئو",
            {
                "description": "تمام عنوان‌های سایت، نام برند، تگ‌لاین، متاتگ‌ها و هویت پنل مدیریت از این بخش خوانده می‌شود.",
                "fields": (
                    "site_branding",
                    "site_logo",
                    "site_logo_preview",
                    "site_favicon",
                    "site_favicon_preview",
                    "site_og_image",
                    "site_og_image_preview",
                    "page_seo",
                ),
            },
        ),
        (
            "رنگ‌ها و صفحات رویداد",
            {
                "description": "پالت رنگی سایت و محتوای صفحات رویداد مانند فینگر فود، ترحیم، حلوا و گل از این بخش مدیریت می‌شود.",
                "fields": ("theme_palette", "event_pages"),
            },
        ),
        (
            "قوانین سفارش و ارسال",
            {
                "fields": (
                    "min_order_qty",
                    "lead_time_hours",
                    "allowed_provinces",
                    "delivery_windows",
                    "payment_methods",
                ),
            },
        ),
        (
            "محتوای داینامیک صفحه اصلی",
            {
                "fields": ("site_top_notice", "homepage_benefits_section", "updated_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        if SiteSetting.objects.exists():
            return False
        return super().has_add_permission(request)

    @admin.display(description="نام برند")
    def site_name_display(self, obj: SiteSetting) -> str:
        branding = obj.site_branding if isinstance(obj.site_branding, dict) else {}
        return str(branding.get("site_name") or "تنظیمات سایت")

    @admin.display(description="پیش‌نمایش لوگو")
    def site_logo_preview(self, obj: SiteSetting | None) -> str:
        return self._render_image_preview(
            getattr(obj, "site_logo", None),
            empty_message="لوگوی سایت هنوز بارگذاری نشده است.",
        )

    @admin.display(description="پیش‌نمایش فاوآیکن")
    def site_favicon_preview(self, obj: SiteSetting | None) -> str:
        return self._render_image_preview(
            getattr(obj, "site_favicon", None),
            empty_message="فاوآیکن سایت هنوز بارگذاری نشده است.",
            preview_size=80,
        )

    @admin.display(description="پیش‌نمایش تصویر اشتراک‌گذاری")
    def site_og_image_preview(self, obj: SiteSetting | None) -> str:
        return self._render_image_preview(
            getattr(obj, "site_og_image", None),
            empty_message="تصویر پیش‌فرض شبکه‌های اجتماعی هنوز بارگذاری نشده است.",
            preview_size=220,
            preview_ratio="aspect-ratio: 1200 / 630;",
        )

    def _render_image_preview(
        self,
        field,
        *,
        empty_message: str,
        preview_size: int = 140,
        preview_ratio: str = "",
    ) -> str:
        if field and getattr(field, "url", ""):
            return format_html(
                (
                    '<div class="admin-image-preview-card">'
                    '<img src="{}" alt="" class="admin-image-preview-card__image" '
                    'style="max-width: {}px; max-height: {}px; {}" />'
                    '<a href="{}" target="_blank" rel="noopener noreferrer" '
                    'class="admin-image-preview-card__link">مشاهده فایل اصلی</a>'
                    "</div>"
                ),
                field.url,
                preview_size,
                preview_size,
                preview_ratio,
                field.url,
            )

        return format_html(
            '<div class="admin-image-preview-card admin-image-preview-card--empty">{}</div>',
            empty_message,
        )

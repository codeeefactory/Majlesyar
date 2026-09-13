from django.contrib import admin, messages
from django.utils import timezone

from config.admin_mixins import PersianAdminFormMixin

from .models import Order, OrderItem, OrderNote


class OrderItemInline(PersianAdminFormMixin, admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderNoteInline(PersianAdminFormMixin, admin.TabularInline):
    model = OrderNote
    extra = 0
    readonly_fields = ("created_at", "created_by")


@admin.action(description="سفارش های انتخاب شده را تایید کن")
def mark_confirmed(modeladmin, request, queryset):
    updated = queryset.update(status=Order.Status.CONFIRMED)
    modeladmin.message_user(request, f"{updated} سفارش تایید شد.", level=messages.SUCCESS)


@admin.action(description="سفارش های انتخاب شده را در حال آماده سازی کن")
def mark_preparing(modeladmin, request, queryset):
    updated = queryset.update(status=Order.Status.PREPARING)
    modeladmin.message_user(request, f"{updated} سفارش در حال آماده‌سازی شد.", level=messages.SUCCESS)


@admin.action(description="سفارش های انتخاب شده را ارسال شده کن")
def mark_shipped(modeladmin, request, queryset):
    updated = queryset.update(status=Order.Status.SHIPPED)
    modeladmin.message_user(request, f"{updated} سفارش ارسال‌شده شد.", level=messages.SUCCESS)


@admin.action(description="سفارش های انتخاب شده را تحویل شده کن")
def mark_delivered(modeladmin, request, queryset):
    updated = queryset.update(status=Order.Status.DELIVERED)
    modeladmin.message_user(request, f"{updated} سفارش تحویل‌شده شد.", level=messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("public_id", "customer_name", "status", "formatted_total", "created_local")
    list_filter = ()
    search_fields = ("public_id", "customer_name", "customer_phone")
    inlines = (OrderItemInline, OrderNoteInline)
    actions = (mark_confirmed, mark_preparing, mark_shipped, mark_delivered)
    readonly_fields = ("public_id", "created_at", "updated_at")
    fieldsets = (
        (
            "اطلاعات سفارش",
            {
                "description": "راهنما: وضعیت و کد سفارش را بررسی کنید.",
                "fields": ("public_id", "status", "total", "payment_method"),
            },
        ),
        (
            "اطلاعات مشتری",
            {
                "description": "نکته: اطلاعات تماس باید دقیق و قابل پیگیری باشد.",
                "fields": (
                    "customer_name",
                    "customer_phone",
                    "customer_province",
                    "customer_address",
                    "customer_notes",
                ),
            },
        ),
        (
            "تحویل",
            {
                "description": "راهنما: تاریخ و بازه تحویل را مطابق درخواست مشتری ثبت کنید.",
                "fields": ("delivery_date", "delivery_window"),
            },
        ),
        (
            "زمان بندی",
            {
                "description": "نکته: این فیلدها خودکار هستند.",
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="مبلغ کل")
    def formatted_total(self, obj: Order) -> str:
        return f"{obj.total:,} تومان"

    @admin.display(description="زمان ثبت")
    def created_local(self, obj: Order) -> str:
        return timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")


@admin.register(OrderItem)
class OrderItemAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("order", "name", "quantity", "price", "is_custom_pack")
    list_filter = ()
    search_fields = ("order__public_id", "name")
    fieldsets = (
        (
            "اطلاعات آیتم سفارش",
            {
                "description": "راهنما: مشخصات آیتم را دقیق وارد کنید.",
                "fields": ("order", "product", "name", "quantity", "price", "is_custom_pack", "custom_config"),
            },
        ),
    )


@admin.register(OrderNote)
class OrderNoteAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("order", "short_note", "created_at", "created_by")
    search_fields = ("order__public_id", "note")
    readonly_fields = ("created_at", "created_by")
    fieldsets = (
        (
            "یادداشت سفارش",
            {
                "description": "نکته: این یادداشت ها برای پیگیری داخلی تیم است.",
                "fields": ("order", "note", "created_at", "created_by"),
            },
        ),
    )

    @admin.display(description="خلاصه یادداشت")
    def short_note(self, obj: OrderNote) -> str:
        return obj.note[:60]

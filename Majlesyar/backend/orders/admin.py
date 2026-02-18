from django.contrib import admin
from django.utils import timezone

from .models import Order, OrderItem, OrderNote


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderNoteInline(admin.TabularInline):
    model = OrderNote
    extra = 0
    readonly_fields = ("created_at", "created_by")


@admin.action(description="Mark selected orders as confirmed")
def mark_confirmed(modeladmin, request, queryset):
    queryset.update(status=Order.Status.CONFIRMED)


@admin.action(description="Mark selected orders as preparing")
def mark_preparing(modeladmin, request, queryset):
    queryset.update(status=Order.Status.PREPARING)


@admin.action(description="Mark selected orders as shipped")
def mark_shipped(modeladmin, request, queryset):
    queryset.update(status=Order.Status.SHIPPED)


@admin.action(description="Mark selected orders as delivered")
def mark_delivered(modeladmin, request, queryset):
    queryset.update(status=Order.Status.DELIVERED)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "customer_name", "status", "formatted_total", "created_local")
    list_filter = ("status", "delivery_date", "customer_province")
    search_fields = ("public_id", "customer_name", "customer_phone")
    inlines = (OrderItemInline, OrderNoteInline)
    actions = (mark_confirmed, mark_preparing, mark_shipped, mark_delivered)
    readonly_fields = ("public_id", "created_at", "updated_at")

    @admin.display(description="Total")
    def formatted_total(self, obj: Order) -> str:
        return f"{obj.total:,} تومان"

    @admin.display(description="Created At")
    def created_local(self, obj: Order) -> str:
        return timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "quantity", "price", "is_custom_pack")
    list_filter = ("is_custom_pack",)
    search_fields = ("order__public_id", "name")


@admin.register(OrderNote)
class OrderNoteAdmin(admin.ModelAdmin):
    list_display = ("order", "short_note", "created_at", "created_by")
    search_fields = ("order__public_id", "note")

    @admin.display(description="Note")
    def short_note(self, obj: OrderNote) -> str:
        return obj.note[:60]

# Register your models here.

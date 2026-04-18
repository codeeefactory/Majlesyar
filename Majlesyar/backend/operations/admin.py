from django.contrib import admin

from .models import ClientProfile, Invoice, InvoiceLineItem, OperationsAuditLog, SmsLog, SmsTemplate


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "province", "memorial_date", "is_active")
    search_fields = ("full_name", "phone", "deceased_name")
    list_filter = ("province", "is_active")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "client", "status", "total_amount", "issue_date")
    list_filter = ("status", "issue_date")
    search_fields = ("invoice_number", "client__full_name", "client__phone")
    inlines = [InvoiceLineItemInline]


@admin.register(SmsTemplate)
class SmsTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_active", "updated_at")
    list_filter = ("is_active", "code")


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ("client", "event_type", "status", "recipient", "created_at")
    list_filter = ("status", "event_type")
    search_fields = ("client__full_name", "recipient", "body")


@admin.register(OperationsAuditLog)
class OperationsAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "actor", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action")

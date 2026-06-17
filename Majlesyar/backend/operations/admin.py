from django.contrib import admin

from config.admin_mixins import PersianAdminFormMixin

from .models import ClientProfile, Invoice, InvoiceLineItem, OperationsAuditLog, SmsLog, SmsTemplate


class InvoiceLineItemInline(PersianAdminFormMixin, admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    fields = ("description", "quantity", "unit_price", "discount_amount")


@admin.register(ClientProfile)
class ClientProfileAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("full_name", "phone", "province", "memorial_date", "is_active")
    search_fields = ("full_name", "phone", "deceased_name")
    list_filter = ("province", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Customer basics",
            {
                "description": "Beginner guide: enter the real customer/contact person here. Phone must be reachable.",
                "fields": ("full_name", "phone", "email", "is_active"),
            },
        ),
        (
            "Address",
            {
                "description": "Beginner guide: province/city help delivery and follow-up. Address can stay empty until order/invoice is real.",
                "fields": ("province", "city", "address"),
            },
        ),
        (
            "Memorial details",
            {
                "description": "Beginner guide: fill these only when the customer is for memorial/reminder services.",
                "fields": ("deceased_name", "memorial_date", "memorial_location", "notes"),
            },
        ),
        (
            "Internal tracking",
            {
                "description": "System fields. Usually leave them unchanged.",
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )


@admin.register(Invoice)
class InvoiceAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("invoice_number", "client", "status", "total_amount", "issue_date")
    list_filter = ("status", "issue_date")
    search_fields = ("invoice_number", "client__full_name", "client__phone")
    inlines = [InvoiceLineItemInline]
    readonly_fields = ("invoice_number", "subtotal_amount", "total_amount", "created_at", "updated_at")
    fieldsets = (
        (
            "Invoice basics",
            {
                "description": "Beginner guide: choose customer, then set status. Invoice number is created automatically.",
                "fields": ("invoice_number", "client", "status", "issue_date", "due_date"),
            },
        ),
        (
            "Costs",
            {
                "description": "Beginner guide: add products/services in line items below. Totals recalculate automatically after save.",
                "fields": ("discount_amount", "fee_amount", "tax_amount", "subtotal_amount", "total_amount"),
            },
        ),
        (
            "Notes and tracking",
            {
                "description": "Internal notes are for staff. They are not public website text.",
                "fields": ("notes", "created_by", "created_at", "updated_at"),
            },
        ),
    )


@admin.register(SmsTemplate)
class SmsTemplateAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("title", "code", "is_active", "updated_at")
    list_filter = ("is_active", "code")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Template content",
            {
                "description": "Beginner guide: code decides when this SMS is used. Body is the text customers receive.",
                "fields": ("code", "title", "body", "is_active"),
            },
        ),
        (
            "System time",
            {
                "description": "System fields. No need to edit.",
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(SmsLog)
class SmsLogAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("client", "event_type", "status", "recipient", "created_at")
    list_filter = ("status", "event_type")
    search_fields = ("client__full_name", "recipient", "body")
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "SMS message",
            {
                "description": "Beginner guide: each row is one SMS attempt. Check status and error message when sending fails.",
                "fields": ("client", "template", "event_type", "recipient", "body", "status"),
            },
        ),
        (
            "Provider result",
            {
                "description": "Technical delivery result from SMS provider. Staff usually only reads this for troubleshooting.",
                "fields": ("provider", "provider_message_id", "provider_response", "error_message", "sent_by", "sent_at", "created_at"),
            },
        ),
    )


@admin.register(OperationsAuditLog)
class OperationsAuditLogAdmin(PersianAdminFormMixin, admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "actor", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action")
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "Audit event",
            {
                "description": "Beginner guide: audit rows explain who did what. Do not edit unless correcting a test record.",
                "fields": ("actor", "action", "entity_type", "entity_id", "metadata", "created_at"),
            },
        ),
    )

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
import uuid

from .services import (
    ANNIVERSARY_TEMPLATE_CODE,
    DEFAULT_TEMPLATE_BODIES,
    FORTIETH_TEMPLATE_CODE,
    InvoiceLineCalculation,
    calculate_invoice_totals,
    calculate_reminder_dates,
)


User = get_user_model()
iran_phone_validator = RegexValidator(r"^09\d{9}$", "شماره موبایل باید با فرمت 09xxxxxxxxx باشد.")


class ClientProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, validators=[iran_phone_validator], db_index=True)
    email = models.EmailField(blank=True)
    province = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True)
    address = models.TextField(blank=True)
    deceased_name = models.CharField(max_length=255, blank=True)
    memorial_date = models.DateField(blank=True, null=True, db_index=True)
    memorial_location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_clients",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Client profile"
        verbose_name_plural = "Client profiles"

    @property
    def fortieth_date(self):
        return calculate_reminder_dates(self.memorial_date)["fortieth_date"]

    @property
    def anniversary_date(self):
        return calculate_reminder_dates(self.memorial_date)["anniversary_date"]

    def __str__(self) -> str:
        return self.full_name


def generate_invoice_number() -> str:
    today = timezone.localdate()
    prefix = f"INV-{today.strftime('%Y%m%d')}-"
    latest_invoice = (
        Invoice.objects.filter(invoice_number__startswith=prefix)
        .order_by("-invoice_number")
        .values_list("invoice_number", flat=True)
        .first()
    )
    if latest_invoice:
        try:
            latest_sequence = int(str(latest_invoice).rsplit("-", 1)[-1])
        except ValueError:
            latest_sequence = 0
    else:
        latest_sequence = 0
    return f"{prefix}{latest_sequence + 1:03d}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=32, unique=True, db_index=True, blank=True)
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="invoices")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    discount_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    fee_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    tax_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    subtotal_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    total_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            candidate = generate_invoice_number()
            while Invoice.objects.exclude(pk=self.pk).filter(invoice_number=candidate).exists():
                candidate = generate_invoice_number()
            self.invoice_number = candidate
        super().save(*args, **kwargs)

    def recalculate_totals(self, *, persist: bool = True) -> dict[str, int]:
        lines = [
            InvoiceLineCalculation(
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_amount=line.discount_amount,
            )
            for line in self.line_items.all()
        ]
        totals = calculate_invoice_totals(
            lines,
            discount_amount=self.discount_amount,
            fee_amount=self.fee_amount,
            tax_amount=self.tax_amount,
        )
        self.subtotal_amount = totals["subtotal_amount"]
        self.total_amount = totals["total_amount"]
        if persist:
            Invoice.objects.filter(pk=self.pk).update(
                subtotal_amount=self.subtotal_amount,
                total_amount=self.total_amount,
                updated_at=timezone.now(),
            )
        return totals

    def __str__(self) -> str:
        return self.invoice_number


class InvoiceLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    discount_amount = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Invoice line item"
        verbose_name_plural = "Invoice line items"

    @property
    def line_total(self) -> int:
        return max(self.quantity * self.unit_price - self.discount_amount, 0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.recalculate_totals()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate_totals()

    def __str__(self) -> str:
        return self.description


class SmsTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Code(models.TextChoices):
        FORTIETH_DAY = FORTIETH_TEMPLATE_CODE, "40th day reminder"
        ANNIVERSARY_DAY = ANNIVERSARY_TEMPLATE_CODE, "365th day reminder"
        MANUAL = "manual", "Manual"

    code = models.CharField(max_length=32, choices=Code.choices, unique=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "SMS template"
        verbose_name_plural = "SMS templates"

    def save(self, *args, **kwargs):
        if not self.body and self.code in DEFAULT_TEMPLATE_BODIES:
            self.body = DEFAULT_TEMPLATE_BODIES[self.code]
        if not self.title:
            self.title = dict(self.Code.choices).get(self.code, self.code)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class SmsLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="sms_logs")
    template = models.ForeignKey(
        SmsTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    event_type = models.CharField(max_length=32, blank=True)
    recipient = models.CharField(max_length=32)
    body = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=32, default="kavenegar")
    provider_message_id = models.CharField(max_length=128, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    sent_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_sms_logs",
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS log"
        verbose_name_plural = "SMS logs"

    def __str__(self) -> str:
        return f"{self.client.full_name} - {self.status}"


class OperationsAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operations_audit_logs",
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Operations audit log"
        verbose_name_plural = "Operations audit logs"

    def __str__(self) -> str:
        return f"{self.action} ({self.entity_type})"

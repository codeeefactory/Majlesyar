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
    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField("نام کامل مشتری", max_length=255)
    phone = models.CharField("شماره موبایل", max_length=32, validators=[iran_phone_validator], db_index=True)
    email = models.EmailField("ایمیل", blank=True)
    province = models.CharField("استان", max_length=128, blank=True)
    city = models.CharField("شهر", max_length=128, blank=True)
    address = models.TextField("آدرس", blank=True)
    deceased_name = models.CharField("نام مرحوم/مرحومه", max_length=255, blank=True)
    memorial_date = models.DateField("تاریخ مراسم", blank=True, null=True, db_index=True)
    memorial_location = models.CharField("محل مراسم", max_length=255, blank=True)
    notes = models.TextField("یادداشت داخلی", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_by = models.ForeignKey(
        User,
        verbose_name="ثبت‌کننده",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_clients",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "پرونده مشتری"
        verbose_name_plural = "پرونده‌های مشتریان"

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
        DRAFT = "draft", "پیش‌نویس"
        SENT = "sent", "ارسال‌شده"
        PAID = "paid", "پرداخت‌شده"
        CANCELLED = "cancelled", "لغوشده"

    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField("شماره فاکتور", max_length=32, unique=True, db_index=True, blank=True)
    client = models.ForeignKey(ClientProfile, verbose_name="مشتری", on_delete=models.CASCADE, related_name="invoices")
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField("تاریخ صدور", default=timezone.localdate)
    due_date = models.DateField("مهلت پرداخت", blank=True, null=True)
    notes = models.TextField("یادداشت", blank=True)
    discount_amount = models.PositiveIntegerField("مبلغ تخفیف", default=0, validators=[MinValueValidator(0)])
    fee_amount = models.PositiveIntegerField("هزینه اضافه", default=0, validators=[MinValueValidator(0)])
    tax_amount = models.PositiveIntegerField("مالیات", default=0, validators=[MinValueValidator(0)])
    subtotal_amount = models.PositiveIntegerField("جمع جزء", default=0, validators=[MinValueValidator(0)])
    total_amount = models.PositiveIntegerField("مبلغ نهایی", default=0, validators=[MinValueValidator(0)])
    created_by = models.ForeignKey(
        User,
        verbose_name="ثبت‌کننده",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_invoices",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        verbose_name = "فاکتور"
        verbose_name_plural = "فاکتورها"

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
    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, verbose_name="فاکتور", on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField("شرح", max_length=255)
    quantity = models.PositiveIntegerField("تعداد", default=1, validators=[MinValueValidator(1)])
    unit_price = models.PositiveIntegerField("قیمت واحد", default=0, validators=[MinValueValidator(0)])
    discount_amount = models.PositiveIntegerField("تخفیف ردیف", default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "ردیف فاکتور"
        verbose_name_plural = "ردیف‌های فاکتور"

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
    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)

    class Code(models.TextChoices):
        FORTIETH_DAY = FORTIETH_TEMPLATE_CODE, "یادآوری چهلم"
        ANNIVERSARY_DAY = ANNIVERSARY_TEMPLATE_CODE, "یادآوری سالگرد"
        MANUAL = "manual", "دستی"

    code = models.CharField("کد قالب", max_length=32, choices=Code.choices, unique=True)
    title = models.CharField("عنوان", max_length=255)
    body = models.TextField("متن پیامک")
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "قالب پیامک"
        verbose_name_plural = "قالب‌های پیامک"

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
        PENDING = "pending", "در انتظار"
        SENT = "sent", "ارسال‌شده"
        FAILED = "failed", "ناموفق"

    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientProfile, verbose_name="مشتری", on_delete=models.CASCADE, related_name="sms_logs")
    template = models.ForeignKey(
        SmsTemplate,
        verbose_name="قالب پیامک",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    event_type = models.CharField("نوع رویداد", max_length=32, blank=True)
    recipient = models.CharField("گیرنده", max_length=32)
    body = models.TextField("متن پیام")
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField("ارائه‌دهنده", max_length=32, default="kavenegar")
    provider_message_id = models.CharField("شناسه پیام در سرویس‌دهنده", max_length=128, blank=True)
    provider_response = models.JSONField("پاسخ سرویس‌دهنده", default=dict, blank=True)
    error_message = models.TextField("پیام خطا", blank=True)
    sent_by = models.ForeignKey(
        User,
        verbose_name="ارسال‌کننده",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_sms_logs",
    )
    sent_at = models.DateTimeField("زمان ارسال", blank=True, null=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "گزارش پیامک"
        verbose_name_plural = "گزارش‌های پیامک"

    def __str__(self) -> str:
        return f"{self.client.full_name} - {self.status}"


class OperationsAuditLog(models.Model):
    id = models.UUIDField("شناسه", primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        User,
        verbose_name="کاربر انجام‌دهنده",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operations_audit_logs",
    )
    action = models.CharField("عملیات", max_length=64)
    entity_type = models.CharField("نوع رکورد", max_length=64)
    entity_id = models.CharField("شناسه رکورد", max_length=64, blank=True)
    metadata = models.JSONField("جزئیات", default=dict, blank=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "گزارش عملیات"
        verbose_name_plural = "گزارش‌های عملیات"

    def __str__(self) -> str:
        return f"{self.action} ({self.entity_type})"

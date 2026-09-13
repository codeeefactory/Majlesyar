from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


class TelegramOperator(models.Model):
    telegram_user_id = models.BigIntegerField("شناسه کاربر تلگرام", unique=True, db_index=True)
    telegram_chat_id = models.BigIntegerField("شناسه گفتگو تلگرام", blank=True, null=True, db_index=True)
    username = models.CharField("نام کاربری", max_length=255, blank=True)
    first_name = models.CharField("نام", max_length=255, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=255, blank=True)
    django_user = models.ForeignKey(
        User,
        verbose_name="کاربر پنل",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_operators",
    )
    is_active = models.BooleanField("فعال", default=True)
    notifications_enabled = models.BooleanField("دریافت اعلان", default=True)
    last_seen_at = models.DateTimeField("آخرین بازدید", blank=True, null=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["telegram_user_id"]
        verbose_name = "اپراتور تلگرام"
        verbose_name_plural = "اپراتورهای تلگرام"

    @property
    def display_name(self) -> str:
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part).strip()
        return full_name or self.username or str(self.telegram_user_id)

    def __str__(self) -> str:
        return self.display_name


class TelegramUpdateReceipt(models.Model):
    class Status(models.TextChoices):
        PROCESSED = "processed", "پردازش‌شده"
        FAILED = "failed", "ناموفق"
        IGNORED = "ignored", "نادیده‌گرفته‌شده"

    update_id = models.BigIntegerField("شناسه آپدیت", unique=True, db_index=True)
    source = models.CharField("منبع", max_length=32, default="webhook")
    payload = models.JSONField("داده خام", default=dict, blank=True)
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.PROCESSED)
    error_message = models.TextField("پیام خطا", blank=True)
    processed_at = models.DateTimeField("زمان پردازش", auto_now_add=True)

    class Meta:
        ordering = ["-update_id"]
        verbose_name = "دریافت پیام تلگرام"
        verbose_name_plural = "دریافت‌های پیام تلگرام"

    def __str__(self) -> str:
        return str(self.update_id)


class TelegramBotAuditLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "موفق"
        DENIED = "denied", "ردشده"
        FAILED = "failed", "ناموفق"
        IGNORED = "ignored", "نادیده‌گرفته‌شده"
        PENDING = "pending", "در انتظار"

    telegram_user_id = models.BigIntegerField("شناسه کاربر تلگرام", blank=True, null=True, db_index=True)
    telegram_chat_id = models.BigIntegerField("شناسه گفتگو تلگرام", blank=True, null=True, db_index=True)
    operator = models.ForeignKey(
        TelegramOperator,
        verbose_name="اپراتور",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    django_user = models.ForeignKey(
        User,
        verbose_name="کاربر پنل",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_bot_audit_logs",
    )
    command = models.CharField("دستور", max_length=128)
    action = models.CharField("عملیات", max_length=128, blank=True)
    target_type = models.CharField("نوع هدف", max_length=128, blank=True)
    target_identifier = models.CharField("شناسه هدف", max_length=255, blank=True)
    previous_state = models.JSONField("وضعیت قبلی", blank=True, null=True)
    new_state = models.JSONField("وضعیت جدید", blank=True, null=True)
    metadata = models.JSONField("جزئیات", default=dict, blank=True)
    status = models.CharField("وضعیت", max_length=16, choices=Status.choices, default=Status.SUCCESS)
    error_message = models.TextField("پیام خطا", blank=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "گزارش ربات تلگرام"
        verbose_name_plural = "گزارش‌های ربات تلگرام"

    def __str__(self) -> str:
        return f"{self.command} ({self.status})"


class TelegramConfirmation(models.Model):
    token = models.UUIDField("توکن تأیید", default=uuid.uuid4, unique=True, editable=False, db_index=True)
    operator = models.ForeignKey(
        TelegramOperator,
        verbose_name="اپراتور",
        on_delete=models.CASCADE,
        related_name="confirmations",
    )
    telegram_user_id = models.BigIntegerField("شناسه کاربر تلگرام", db_index=True)
    telegram_chat_id = models.BigIntegerField("شناسه گفتگو تلگرام", db_index=True)
    action = models.CharField("عملیات", max_length=128)
    command = models.CharField("دستور", max_length=128, blank=True)
    target_type = models.CharField("نوع هدف", max_length=128, blank=True)
    target_identifier = models.CharField("شناسه هدف", max_length=255, blank=True)
    payload = models.JSONField("داده‌ها", default=dict, blank=True)
    audit_log = models.ForeignKey(
        TelegramBotAuditLog,
        verbose_name="گزارش مرتبط",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmations",
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    expires_at = models.DateTimeField("زمان انقضا")
    consumed_at = models.DateTimeField("زمان استفاده", blank=True, null=True)
    cancelled_at = models.DateTimeField("زمان لغو", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تأیید تلگرام"
        verbose_name_plural = "تأییدهای تلگرام"

    @classmethod
    def create_for_action(
        cls,
        *,
        operator: TelegramOperator,
        telegram_user_id: int,
        telegram_chat_id: int,
        action: str,
        command: str,
        target_type: str,
        target_identifier: str,
        payload: dict,
        audit_log: TelegramBotAuditLog | None = None,
    ) -> "TelegramConfirmation":
        ttl_seconds = settings.TELEGRAM_BOT["CONFIRMATION_TTL_SECONDS"]
        return cls.objects.create(
            operator=operator,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            action=action,
            command=command,
            target_type=target_type,
            target_identifier=target_identifier,
            payload=payload,
            audit_log=audit_log,
            expires_at=timezone.now() + timezone.timedelta(seconds=ttl_seconds),
        )

    @property
    def is_active(self) -> bool:
        return (
            self.consumed_at is None
            and self.cancelled_at is None
            and self.expires_at >= timezone.now()
        )

    def mark_consumed(self) -> None:
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])

    def mark_cancelled(self) -> None:
        self.cancelled_at = timezone.now()
        self.save(update_fields=["cancelled_at"])

    def __str__(self) -> str:
        return f"{self.action}:{self.token}"


class TelegramBotState(models.Model):
    key = models.CharField("کلید", max_length=128, unique=True)
    value = models.JSONField("مقدار", default=dict, blank=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "وضعیت ربات تلگرام"
        verbose_name_plural = "وضعیت‌های ربات تلگرام"

    def __str__(self) -> str:
        return self.key

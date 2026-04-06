from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


class TelegramOperator(models.Model):
    telegram_user_id = models.BigIntegerField(unique=True, db_index=True)
    telegram_chat_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    username = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    django_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_operators",
    )
    is_active = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["telegram_user_id"]
        verbose_name = "Telegram operator"
        verbose_name_plural = "Telegram operators"

    @property
    def display_name(self) -> str:
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part).strip()
        return full_name or self.username or str(self.telegram_user_id)

    def __str__(self) -> str:
        return self.display_name


class TelegramUpdateReceipt(models.Model):
    class Status(models.TextChoices):
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    update_id = models.BigIntegerField(unique=True, db_index=True)
    source = models.CharField(max_length=32, default="webhook")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROCESSED)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-update_id"]
        verbose_name = "Telegram update receipt"
        verbose_name_plural = "Telegram update receipts"

    def __str__(self) -> str:
        return str(self.update_id)


class TelegramBotAuditLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"
        PENDING = "pending", "Pending"

    telegram_user_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    telegram_chat_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    operator = models.ForeignKey(
        TelegramOperator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    django_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_bot_audit_logs",
    )
    command = models.CharField(max_length=128)
    action = models.CharField(max_length=128, blank=True)
    target_type = models.CharField(max_length=128, blank=True)
    target_identifier = models.CharField(max_length=255, blank=True)
    previous_state = models.JSONField(blank=True, null=True)
    new_state = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Telegram bot audit log"
        verbose_name_plural = "Telegram bot audit logs"

    def __str__(self) -> str:
        return f"{self.command} ({self.status})"


class TelegramConfirmation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    operator = models.ForeignKey(
        TelegramOperator,
        on_delete=models.CASCADE,
        related_name="confirmations",
    )
    telegram_user_id = models.BigIntegerField(db_index=True)
    telegram_chat_id = models.BigIntegerField(db_index=True)
    action = models.CharField(max_length=128)
    command = models.CharField(max_length=128, blank=True)
    target_type = models.CharField(max_length=128, blank=True)
    target_identifier = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    audit_log = models.ForeignKey(
        TelegramBotAuditLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Telegram confirmation"
        verbose_name_plural = "Telegram confirmations"

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
    key = models.CharField(max_length=128, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "Telegram bot state"
        verbose_name_plural = "Telegram bot states"

    def __str__(self) -> str:
        return self.key


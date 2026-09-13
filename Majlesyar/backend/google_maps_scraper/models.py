from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class MapsScrapeJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        WORKING = "working", "در حال اجرا"
        OK = "ok", "تکمیل‌شده"
        FAILED = "failed", "ناموفق"
        DELETED = "deleted", "حذف‌شده"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upstream_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    keywords = models.JSONField(default=list)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    request_payload = models.JSONField(default=dict)
    upstream_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maps_scrape_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "استخراج نقشه"
        verbose_name_plural = "استخراج‌های نقشه"

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

from django.db import models
from django.core.validators import MinValueValidator


class SiteSetting(models.Model):
    """
    Singleton model for global storefront settings.
    Always persisted with primary key = 1.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    min_order_qty = models.PositiveIntegerField(default=40, validators=[MinValueValidator(1)])
    lead_time_hours = models.PositiveIntegerField(default=48, validators=[MinValueValidator(0)])
    allowed_provinces = models.JSONField(default=list, blank=True)
    delivery_windows = models.JSONField(default=list, blank=True)
    payment_methods = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self) -> str:
        return "Global Site Settings"

# Create your models here.

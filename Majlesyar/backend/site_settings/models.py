from django.core.validators import MinValueValidator
from django.db import models


class SiteSetting(models.Model):
    """
    Single-record model for global storefront settings.
    Always stored with primary key 1.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    min_order_qty = models.PositiveIntegerField(default=40, validators=[MinValueValidator(1)])
    lead_time_hours = models.PositiveIntegerField(default=48, validators=[MinValueValidator(0)])
    allowed_provinces = models.JSONField(default=list, blank=True)
    delivery_windows = models.JSONField(default=list, blank=True)
    payment_methods = models.JSONField(default=list, blank=True)
    contact_phone = models.CharField(max_length=32, default="+989915505141", blank=True)
    contact_address = models.TextField(
        default="تهران، امیرآباد، خیابان کارگر شمالی، خیابان فرشی مقدم(شانزدهم)، پلاک ۹۱، واحد۶.",
        blank=True,
    )
    working_hours = models.CharField(
        max_length=255,
        default="شنبه تا پنجشنبه ۹ صبح تا ۹ شب",
        blank=True,
    )
    instagram_url = models.URLField(max_length=500, default="https://instagram.com/majlesyar", blank=True)
    telegram_url = models.URLField(max_length=500, default="https://t.me/majlesyar", blank=True)
    whatsapp_url = models.URLField(max_length=500, default="https://wa.me/989915505141", blank=True)
    bale_url = models.URLField(max_length=500, default="https://ble.ir/majlesyar", blank=True)
    maps_url = models.URLField(max_length=500, default="https://maps.google.com/?q=Tehran,Valiasr", blank=True)
    maps_embed_url = models.URLField(
        max_length=1000,
        default="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3239.9627430068!2d51.4066!3d35.7219!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMzXCsDQzJzE4LjgiTiA1McKwMjQnMjMuOCJF!5e0!3m2!1sen!2s!4v1699999999999!5m2!1sen!2s",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSetting":
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self) -> str:
        return "تنظیمات سراسری سایت"

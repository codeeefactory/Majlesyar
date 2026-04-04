from rest_framework import serializers

from .models import SiteSetting


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = (
            "min_order_qty",
            "lead_time_hours",
            "allowed_provinces",
            "delivery_windows",
            "payment_methods",
            "contact_phone",
            "contact_address",
            "working_hours",
            "instagram_url",
            "telegram_url",
            "whatsapp_url",
            "bale_url",
            "maps_url",
            "maps_embed_url",
        )

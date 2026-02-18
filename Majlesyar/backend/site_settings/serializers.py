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
        )

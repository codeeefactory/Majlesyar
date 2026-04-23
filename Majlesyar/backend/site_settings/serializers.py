from rest_framework import serializers

from .models import SiteSetting


class SiteSettingSerializer(serializers.ModelSerializer):
    site_logo = serializers.SerializerMethodField()
    site_favicon = serializers.SerializerMethodField()
    site_og_image = serializers.SerializerMethodField()

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
            "site_logo",
            "site_favicon",
            "site_og_image",
            "site_branding",
            "theme_palette",
            "page_seo",
            "event_pages",
            "site_top_notice",
            "homepage_benefits_section",
        )

    def _build_absolute_media_url(self, field) -> str | None:
        if not field:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(field.url)
        return field.url

    def get_site_logo(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_logo)

    def get_site_favicon(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_favicon)

    def get_site_og_image(self, obj: SiteSetting) -> str | None:
        return self._build_absolute_media_url(obj.site_og_image)


class SiteSettingWriteSerializer(serializers.ModelSerializer):
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
            "site_logo",
            "site_favicon",
            "site_og_image",
            "site_branding",
            "theme_palette",
            "page_seo",
            "event_pages",
            "site_top_notice",
            "homepage_benefits_section",
        )

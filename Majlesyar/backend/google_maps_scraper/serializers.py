from __future__ import annotations

from rest_framework import serializers

from .models import MapsScrapeJob


class MapsScrapeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, default="Majlesyar scrape")
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=300, trim_whitespace=True),
        min_length=1,
        max_length=50,
    )
    lat = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-90, max_value=90)
    lon = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-180, max_value=180)
    lang = serializers.CharField(max_length=10, default="fa")
    zoom = serializers.IntegerField(min_value=1, max_value=21, default=15)
    radius = serializers.IntegerField(min_value=100, max_value=100000, default=10000)
    depth = serializers.IntegerField(min_value=1, max_value=100, default=5)
    email = serializers.BooleanField(default=True)
    fast_mode = serializers.BooleanField(default=False)
    max_time = serializers.IntegerField(min_value=30, max_value=7200, default=600)
    proxies = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=50,
        write_only=True,
    )

    def validate_keywords(self, value):
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not cleaned:
            raise serializers.ValidationError("At least one non-empty keyword is required.")
        return cleaned

    def to_upstream_payload(self) -> dict:
        data = dict(self.validated_data)
        data["lat"] = str(data["lat"])
        data["lon"] = str(data["lon"])
        return data


class MapsScrapeJobSerializer(serializers.ModelSerializer):
    risk_warning = serializers.SerializerMethodField()

    class Meta:
        model = MapsScrapeJob
        fields = (
            "id",
            "upstream_id",
            "name",
            "keywords",
            "latitude",
            "longitude",
            "status",
            "result_count",
            "error_message",
            "request_payload",
            "upstream_payload",
            "risk_warning",
            "created_at",
            "updated_at",
            "completed_at",
        )

    def get_risk_warning(self, obj) -> str | None:
        depth = int(obj.request_payload.get("depth", 0))
        if depth >= 15 or len(obj.keywords) >= 10:
            return "High-volume scraping can temporarily rate-limit the server IP; lower depth or configure proxies."
        return None

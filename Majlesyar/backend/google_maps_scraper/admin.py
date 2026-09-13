from django.contrib import admin

from .models import MapsScrapeJob


@admin.register(MapsScrapeJob)
class MapsScrapeJobAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "result_count", "created_by", "created_at", "completed_at")
    search_fields = ("name", "upstream_id")
    readonly_fields = (
        "id",
        "upstream_id",
        "request_payload",
        "upstream_payload",
        "result_count",
        "created_by",
        "created_at",
        "updated_at",
        "completed_at",
    )
    list_filter = ()

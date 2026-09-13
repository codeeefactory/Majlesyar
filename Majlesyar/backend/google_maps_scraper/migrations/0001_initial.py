import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="MapsScrapeJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("upstream_id", models.CharField(db_index=True, max_length=128, unique=True)),
                ("name", models.CharField(max_length=200)),
                ("keywords", models.JSONField(default=list)),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("request_payload", models.JSONField(default=dict)),
                ("upstream_payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("queued", "در صف"), ("working", "در حال اجرا"), ("ok", "تکمیل‌شده"), ("failed", "ناموفق"), ("deleted", "حذف‌شده")], db_index=True, default="queued", max_length=16)),
                ("result_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="maps_scrape_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "استخراج نقشه", "verbose_name_plural": "استخراج‌های نقشه", "ordering": ["-created_at"]},
        )
    ]

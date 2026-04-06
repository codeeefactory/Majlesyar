from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramBotState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("value", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.CreateModel(
            name="TelegramOperator",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_user_id", models.BigIntegerField(db_index=True, unique=True)),
                ("telegram_chat_id", models.BigIntegerField(blank=True, db_index=True, null=True)),
                ("username", models.CharField(blank=True, max_length=255)),
                ("first_name", models.CharField(blank=True, max_length=255)),
                ("last_name", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("notifications_enabled", models.BooleanField(default=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "django_user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="telegram_operators", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["telegram_user_id"]},
        ),
        migrations.CreateModel(
            name="TelegramUpdateReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("update_id", models.BigIntegerField(db_index=True, unique=True)),
                ("source", models.CharField(default="webhook", max_length=32)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("processed", "Processed"), ("failed", "Failed"), ("ignored", "Ignored")], default="processed", max_length=16)),
                ("error_message", models.TextField(blank=True)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-update_id"]},
        ),
        migrations.CreateModel(
            name="TelegramBotAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_user_id", models.BigIntegerField(blank=True, db_index=True, null=True)),
                ("telegram_chat_id", models.BigIntegerField(blank=True, db_index=True, null=True)),
                ("command", models.CharField(max_length=128)),
                ("action", models.CharField(blank=True, max_length=128)),
                ("target_type", models.CharField(blank=True, max_length=128)),
                ("target_identifier", models.CharField(blank=True, max_length=255)),
                ("previous_state", models.JSONField(blank=True, null=True)),
                ("new_state", models.JSONField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("success", "Success"), ("denied", "Denied"), ("failed", "Failed"), ("ignored", "Ignored"), ("pending", "Pending")], default="success", max_length=16)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "django_user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="telegram_bot_audit_logs", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "operator",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="telegram_bot.telegramoperator"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TelegramConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("telegram_user_id", models.BigIntegerField(db_index=True)),
                ("telegram_chat_id", models.BigIntegerField(db_index=True)),
                ("action", models.CharField(max_length=128)),
                ("command", models.CharField(blank=True, max_length=128)),
                ("target_type", models.CharField(blank=True, max_length=128)),
                ("target_identifier", models.CharField(blank=True, max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "audit_log",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmations", to="telegram_bot.telegrambotauditlog"),
                ),
                (
                    "operator",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="confirmations", to="telegram_bot.telegramoperator"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

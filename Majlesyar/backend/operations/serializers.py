from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import APIException
from rest_framework import serializers

from .models import ClientProfile, Invoice, InvoiceLineItem, OperationsAuditLog, SmsLog, SmsTemplate
from .services import DEFAULT_TEMPLATE_BODIES, calculate_reminder_dates, render_sms_body


User = get_user_model()


class SyncConflictError(APIException):
    status_code = 409
    default_code = "sync_conflict"
    default_detail = "The record changed on the server before this update was applied."


def ensure_sync_base_is_current(*, serializer: serializers.ModelSerializer, attrs: dict, instance) -> dict:
    sync_base_updated_at = attrs.pop("sync_base_updated_at", None)
    if instance is None or sync_base_updated_at is None:
        return attrs
    current_updated_at = getattr(instance, "updated_at", None)
    if current_updated_at and sync_base_updated_at < current_updated_at:
        raise SyncConflictError(
            {
                "detail": "The record has changed on the server. Refresh before applying queued changes.",
                "entity_id": str(instance.pk),
                "entity_type": instance._meta.model_name,
                "current_updated_at": current_updated_at.isoformat(),
                "current_state": serializer.to_representation(instance),
            }
        )
    return attrs


class StaffUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
        )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class StaffUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "password",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ClientProfileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    sync_base_updated_at = serializers.DateTimeField(write_only=True, required=False)
    fortieth_date = serializers.SerializerMethodField()
    anniversary_date = serializers.SerializerMethodField()

    class Meta:
        model = ClientProfile
        fields = (
            "id",
            "full_name",
            "phone",
            "email",
            "province",
            "city",
            "address",
            "deceased_name",
            "memorial_date",
            "fortieth_date",
            "anniversary_date",
            "memorial_location",
            "notes",
            "is_active",
            "sync_base_updated_at",
            "created_at",
            "updated_at",
        )

    def get_fortieth_date(self, obj):
        return obj.fortieth_date.isoformat() if obj.fortieth_date else None

    def get_anniversary_date(self, obj):
        return obj.anniversary_date.isoformat() if obj.anniversary_date else None

    def validate(self, attrs):
        return ensure_sync_base_is_current(serializer=self, attrs=attrs, instance=getattr(self, "instance", None))


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = ("id", "description", "quantity", "unit_price", "discount_amount", "line_total")
        read_only_fields = ("id", "line_total")


class InvoiceSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    sync_base_updated_at = serializers.DateTimeField(write_only=True, required=False)
    line_items = InvoiceLineItemSerializer(many=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "client",
            "client_name",
            "status",
            "issue_date",
            "due_date",
            "notes",
            "discount_amount",
            "fee_amount",
            "tax_amount",
            "subtotal_amount",
            "total_amount",
            "line_items",
            "sync_base_updated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("invoice_number", "subtotal_amount", "total_amount", "created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("sync_base_updated_at", None)
        line_items = validated_data.pop("line_items", [])
        request = self.context.get("request")
        invoice = Invoice.objects.create(
            created_by=getattr(request, "user", None) if request else None,
            **validated_data,
        )
        InvoiceLineItem.objects.bulk_create(
            [InvoiceLineItem(invoice=invoice, **line_item) for line_item in line_items]
        )
        invoice.recalculate_totals()
        invoice.refresh_from_db()
        return invoice

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop("sync_base_updated_at", None)
        line_items = validated_data.pop("line_items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if line_items is not None:
            instance.line_items.all().delete()
            InvoiceLineItem.objects.bulk_create(
                [InvoiceLineItem(invoice=instance, **line_item) for line_item in line_items]
            )
        instance.recalculate_totals()
        instance.refresh_from_db()
        return instance

    def validate(self, attrs):
        return ensure_sync_base_is_current(serializer=self, attrs=attrs, instance=getattr(self, "instance", None))


class SmsTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsTemplate
        fields = ("id", "code", "title", "body", "is_active", "updated_at")
        read_only_fields = ("id", "updated_at")


class SmsLogSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = SmsLog
        fields = (
            "id",
            "client",
            "client_name",
            "template",
            "event_type",
            "recipient",
            "body",
            "status",
            "provider",
            "provider_message_id",
            "error_message",
            "provider_response",
            "sent_at",
            "created_at",
        )


class OperationsAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = OperationsAuditLog
        fields = ("id", "actor_name", "action", "entity_type", "entity_id", "metadata", "created_at")


class ReminderItemSerializer(serializers.ModelSerializer):
    fortieth_date = serializers.SerializerMethodField()
    anniversary_date = serializers.SerializerMethodField()
    next_due_type = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()

    class Meta:
        model = ClientProfile
        fields = (
            "id",
            "full_name",
            "phone",
            "deceased_name",
            "memorial_date",
            "fortieth_date",
            "anniversary_date",
            "next_due_type",
            "next_due_date",
        )

    def _reminder_context(self, obj):
        dates = calculate_reminder_dates(obj.memorial_date)
        today = self.context.get("today")
        due_candidates = []
        if dates["fortieth_date"] and dates["fortieth_date"] >= today:
            due_candidates.append(("fortieth_day", dates["fortieth_date"]))
        if dates["anniversary_date"] and dates["anniversary_date"] >= today:
            due_candidates.append(("anniversary_day", dates["anniversary_date"]))
        due_candidates.sort(key=lambda item: item[1])
        return dates, due_candidates[0] if due_candidates else (None, None)

    def get_fortieth_date(self, obj):
        dates, _ = self._reminder_context(obj)
        return dates["fortieth_date"].isoformat() if dates["fortieth_date"] else None

    def get_anniversary_date(self, obj):
        dates, _ = self._reminder_context(obj)
        return dates["anniversary_date"].isoformat() if dates["anniversary_date"] else None

    def get_next_due_type(self, obj):
        _dates, next_due = self._reminder_context(obj)
        return next_due[0]

    def get_next_due_date(self, obj):
        _dates, next_due = self._reminder_context(obj)
        return next_due[1].isoformat() if next_due[1] else None


class SendReminderSerializer(serializers.Serializer):
    template_code = serializers.ChoiceField(
        choices=[
            (SmsTemplate.Code.FORTIETH_DAY, "40th day reminder"),
            (SmsTemplate.Code.ANNIVERSARY_DAY, "365th day reminder"),
            (SmsTemplate.Code.MANUAL, "Manual"),
        ]
    )
    body_override = serializers.CharField(required=False, allow_blank=False)
    dry_run = serializers.BooleanField(default=False)

    def validate(self, attrs):
        client: ClientProfile = self.context["client"]
        template_code = attrs["template_code"]
        if template_code == SmsTemplate.Code.FORTIETH_DAY and client.fortieth_date is None:
            raise serializers.ValidationError({"template_code": "تاریخ چهلم برای این مشتری قابل محاسبه نیست."})
        if template_code == SmsTemplate.Code.ANNIVERSARY_DAY and client.anniversary_date is None:
            raise serializers.ValidationError({"template_code": "تاریخ سالگرد برای این مشتری قابل محاسبه نیست."})
        return attrs

    def build_preview(self) -> str:
        client: ClientProfile = self.context["client"]
        template_code = self.validated_data["template_code"]
        if self.validated_data.get("body_override"):
            return self.validated_data["body_override"]
        template = SmsTemplate.objects.filter(code=template_code, is_active=True).first()
        body = template.body if template else DEFAULT_TEMPLATE_BODIES.get(template_code, "")
        return render_sms_body(body, client)

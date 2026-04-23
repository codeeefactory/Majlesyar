from __future__ import annotations

from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.permissions import IsStaffUser
from catalog.models import BuilderItem, Category, PageProductPlacement, Product, Tag
from catalog.serializers import (
    BuilderItemSerializer,
    CategorySerializer,
    PagePreviewTargetSerializer,
    PageProductPlacementSerializer,
    ProductSerializer,
    TagSerializer,
)
from catalog.services import get_page_preview_targets
from orders.models import Order
from orders.serializers import OrderSerializer
from site_settings.models import SiteSetting
from site_settings.serializers import SiteSettingSerializer
from telegram_bot.models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)
from telegram_bot.serializers import (
    TelegramBotAuditLogSerializer,
    TelegramBotStateSerializer,
    TelegramConfirmationSerializer,
    TelegramOperatorSerializer,
    TelegramUpdateReceiptSerializer,
)

from .models import ClientProfile, Invoice, OperationsAuditLog, SmsLog, SmsTemplate
from .serializers import (
    ClientProfileSerializer,
    InvoiceSerializer,
    OperationsAuditLogSerializer,
    ReminderItemSerializer,
    SendReminderSerializer,
    SmsLogSerializer,
    SmsTemplateSerializer,
    StaffUserSerializer,
    StaffUserWriteSerializer,
)
from .services import send_sms_via_kavenegar


User = get_user_model()


def build_dashboard_payload(*, today):
    clients = ClientProfile.objects.count()
    invoices = Invoice.objects.count()
    pending_invoices = Invoice.objects.filter(status=Invoice.Status.DRAFT).count()
    sent_sms = SmsLog.objects.filter(status=SmsLog.Status.SENT).count()
    upcoming = ReminderItemSerializer(
        ClientProfile.objects.filter(memorial_date__isnull=False, is_active=True),
        many=True,
        context={"today": today},
    ).data
    return {
        "clients_count": clients,
        "invoices_count": invoices,
        "draft_invoices_count": pending_invoices,
        "sms_sent_count": sent_sms,
        "upcoming_reminders": [item for item in upcoming if item["next_due_date"]][:5],
    }


class StaffUserListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]

    def get_queryset(self):
        queryset = User.objects.filter(is_staff=True).order_by("username")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset

    def get_serializer_class(self):
        return StaffUserWriteSerializer if self.request.method == "POST" else StaffUserSerializer


class StaffUserDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    queryset = User.objects.filter(is_staff=True).order_by("username")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return StaffUserWriteSerializer
        return StaffUserSerializer


class ClientProfileListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = ClientProfileSerializer

    def get_queryset(self):
        queryset = ClientProfile.objects.all().order_by("full_name")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(deceased_name__icontains=search)
            )
        province = self.request.query_params.get("province")
        if province:
            queryset = queryset.filter(province__iexact=province)
        return queryset

    def perform_create(self, serializer):
        client = serializer.save(created_by=self.request.user)
        OperationsAuditLog.objects.create(
            actor=self.request.user,
            action="client_created",
            entity_type="client",
            entity_id=str(client.id),
            metadata={"full_name": client.full_name},
        )


class ClientProfileDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = ClientProfileSerializer
    queryset = ClientProfile.objects.all()

    def perform_update(self, serializer):
        client = serializer.save()
        OperationsAuditLog.objects.create(
            actor=self.request.user,
            action="client_updated",
            entity_type="client",
            entity_id=str(client.id),
            metadata={"full_name": client.full_name},
        )


class InvoiceListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = Invoice.objects.select_related("client").prefetch_related("line_items").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        client_id = self.request.query_params.get("client")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search)
                | Q(client__full_name__icontains=search)
                | Q(client__phone__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        invoice = serializer.save()
        OperationsAuditLog.objects.create(
            actor=self.request.user,
            action="invoice_created",
            entity_type="invoice",
            entity_id=str(invoice.id),
            metadata={"invoice_number": invoice.invoice_number},
        )


class InvoiceDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("client").prefetch_related("line_items").all()

    def perform_update(self, serializer):
        invoice = serializer.save()
        OperationsAuditLog.objects.create(
            actor=self.request.user,
            action="invoice_updated",
            entity_type="invoice",
            entity_id=str(invoice.id),
            metadata={"invoice_number": invoice.invoice_number},
        )


class SmsTemplateListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsStaffUser]
    queryset = SmsTemplate.objects.all()
    serializer_class = SmsTemplateSerializer


class SmsTemplateDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    queryset = SmsTemplate.objects.all()
    serializer_class = SmsTemplateSerializer


class SmsLogListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = SmsLogSerializer

    def get_queryset(self):
        queryset = SmsLog.objects.select_related("client", "template").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


class ReminderListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    serializer_class = ReminderItemSerializer

    def get_queryset(self):
        return ClientProfile.objects.filter(memorial_date__isnull=False, is_active=True).order_by("memorial_date")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["today"] = timezone.localdate()
        return context

    def list(self, request, *args, **kwargs):
        days = int(request.query_params.get("days", "30"))
        today = timezone.localdate()
        until = today + timedelta(days=days)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        data = [
            item
            for item in serializer.data
            if item["next_due_date"] and today.isoformat() <= item["next_due_date"] <= until.isoformat()
        ]
        return Response(data)


class DashboardSummaryAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        today = timezone.localdate()
        return Response(build_dashboard_payload(today=today))


class DesktopBootstrapAPIView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        days = int(request.query_params.get("days", "30"))
        today = timezone.localdate()
        until = today + timedelta(days=days)
        reminder_serializer = ReminderItemSerializer(
            ClientProfile.objects.filter(memorial_date__isnull=False, is_active=True).order_by("memorial_date"),
            many=True,
            context={"today": today},
        )
        reminders = [
            item
            for item in reminder_serializer.data
            if item["next_due_date"] and today.isoformat() <= item["next_due_date"] <= until.isoformat()
        ]
        return Response(
            {
                "server_time": timezone.now().isoformat(),
                "dashboard": build_dashboard_payload(today=today),
                "clients": ClientProfileSerializer(ClientProfile.objects.all().order_by("full_name"), many=True).data,
                "invoices": InvoiceSerializer(
                    Invoice.objects.select_related("client").prefetch_related("line_items").all(),
                    many=True,
                    context={"request": request},
                ).data,
                "reminders": reminders,
                "staff": StaffUserSerializer(User.objects.filter(is_staff=True).order_by("username"), many=True).data,
                "templates": SmsTemplateSerializer(SmsTemplate.objects.all(), many=True).data,
                "recent_sms_logs": SmsLogSerializer(
                    SmsLog.objects.select_related("client", "template").all()[:25],
                    many=True,
                ).data,
                "recent_audit_logs": OperationsAuditLogSerializer(
                    OperationsAuditLog.objects.select_related("actor").all()[:25],
                    many=True,
                ).data,
                "audit_log_count": OperationsAuditLog.objects.count(),
                "sms_log_count": SmsLog.objects.count(),
                "products": ProductSerializer(
                    Product.objects.prefetch_related("categories", "tags").all(),
                    many=True,
                    context={"request": request},
                ).data,
                "categories": CategorySerializer(Category.objects.all(), many=True, context={"request": request}).data,
                "tags": TagSerializer(Tag.objects.all(), many=True).data,
                "builder_items": BuilderItemSerializer(
                    BuilderItem.objects.all(),
                    many=True,
                    context={"request": request},
                ).data,
                "page_preview_targets": PagePreviewTargetSerializer(get_page_preview_targets(), many=True).data,
                "page_product_placements": PageProductPlacementSerializer(
                    PageProductPlacement.objects.select_related("product").prefetch_related("product__categories", "product__tags").all(),
                    many=True,
                    context={"request": request},
                ).data,
                "orders": OrderSerializer(Order.objects.prefetch_related("items", "notes").all(), many=True).data,
                "site_settings": SiteSettingSerializer(SiteSetting.load(), context={"request": request}).data,
                "telegram_operators": TelegramOperatorSerializer(
                    TelegramOperator.objects.select_related("django_user").all(),
                    many=True,
                ).data,
                "telegram_audit_logs": TelegramBotAuditLogSerializer(
                    TelegramBotAuditLog.objects.select_related("operator", "django_user").all()[:50],
                    many=True,
                ).data,
                "telegram_confirmations": TelegramConfirmationSerializer(
                    TelegramConfirmation.objects.select_related("operator").all()[:50],
                    many=True,
                ).data,
                "telegram_update_receipts": TelegramUpdateReceiptSerializer(
                    TelegramUpdateReceipt.objects.all()[:50],
                    many=True,
                ).data,
                "telegram_states": TelegramBotStateSerializer(
                    TelegramBotState.objects.all(),
                    many=True,
                ).data,
            }
        )


class SendReminderAPIView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, client_id):
        client = get_object_or_404(ClientProfile, pk=client_id)
        serializer = SendReminderSerializer(data=request.data, context={"client": client})
        serializer.is_valid(raise_exception=True)
        body = serializer.build_preview()
        template = SmsTemplate.objects.filter(code=serializer.validated_data["template_code"]).first()
        sms_log = SmsLog.objects.create(
            client=client,
            template=template,
            event_type=serializer.validated_data["template_code"],
            recipient=client.phone,
            body=body,
            sent_by=request.user,
        )
        if serializer.validated_data["dry_run"]:
            return Response({"preview": body, "sms_log_id": str(sms_log.id)}, status=status.HTTP_200_OK)

        try:
            response_payload = send_sms_via_kavenegar(receptor=client.phone, message=body)
        except RuntimeError as exc:
            sms_log.status = SmsLog.Status.FAILED
            sms_log.error_message = str(exc)
            sms_log.save(update_fields=["status", "error_message"])
            return Response({"detail": str(exc), "preview": body}, status=status.HTTP_502_BAD_GATEWAY)

        sms_log.status = SmsLog.Status.SENT
        sms_log.provider_response = response_payload
        sms_log.sent_at = timezone.now()
        sms_log.save(update_fields=["status", "provider_response", "sent_at"])
        OperationsAuditLog.objects.create(
            actor=request.user,
            action="sms_sent",
            entity_type="client",
            entity_id=str(client.id),
            metadata={"template_code": serializer.validated_data["template_code"], "recipient": client.phone},
        )
        return Response({"preview": body, "sms_log_id": str(sms_log.id), "status": sms_log.status})


class OperationsAuditLogListAPIView(generics.ListAPIView):
    permission_classes = [IsStaffUser]
    queryset = OperationsAuditLog.objects.select_related("actor").all()
    serializer_class = OperationsAuditLogSerializer


class OfflineSessionImportAPIView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _read_bundle(self, request) -> dict:
        if "session_file" in request.FILES:
            try:
                return json.loads(request.FILES["session_file"].read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("The uploaded offline session file is not valid JSON.") from exc
        if isinstance(request.data, dict) and isinstance(request.data.get("bundle"), dict):
            return request.data["bundle"]
        if isinstance(request.data, dict):
            return dict(request.data)
        raise ValueError("No offline session bundle was provided.")

    def _apply_client_action(self, payload: dict, *, request) -> str:
        instance = ClientProfile.objects.filter(pk=payload.get("id")).first() if payload.get("id") else None
        serializer = ClientProfileSerializer(instance, data=payload, partial=instance is not None)
        serializer.is_valid(raise_exception=True)
        client = serializer.save(created_by=request.user if instance is None else instance.created_by)
        if instance is None and not client.created_by_id:
            client.created_by = request.user
            client.save(update_fields=["created_by"])
            return "created"
        return "updated" if instance is not None else "created"

    def _apply_invoice_action(self, payload: dict, *, request) -> str:
        instance = Invoice.objects.filter(pk=payload.get("id")).first() if payload.get("id") else None
        serializer = InvoiceSerializer(
            instance,
            data=payload,
            partial=instance is not None,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return "updated" if instance is not None else "created"

    def post(self, request):
        try:
            bundle = self._read_bundle(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if bundle.get("bundle_format") != 1 or bundle.get("session_type") != "portable_offline":
            return Response({"detail": "Unsupported MajlesYar offline session bundle."}, status=status.HTTP_400_BAD_REQUEST)

        queued_actions = bundle.get("queued_actions", [])
        if not isinstance(queued_actions, list):
            return Response({"detail": "The offline session queue is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        results = {
            "applied_actions": 0,
            "clients_created": 0,
            "clients_updated": 0,
            "invoices_created": 0,
            "invoices_updated": 0,
        }

        try:
            with transaction.atomic():
                for action in queued_actions:
                    action_type = action.get("action_type")
                    payload = action.get("payload")
                    if not isinstance(payload, dict):
                        raise ValueError("A queued action is missing its payload.")
                    if action_type == "save_client":
                        result_key = self._apply_client_action(payload, request=request)
                        results[f"clients_{result_key}"] += 1
                    elif action_type == "save_invoice":
                        result_key = self._apply_invoice_action(payload, request=request)
                        results[f"invoices_{result_key}"] += 1
                    else:
                        raise ValueError(f"Unsupported queued action: {action_type}")
                    results["applied_actions"] += 1
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        OperationsAuditLog.objects.create(
            actor=request.user,
            action="offline_session_imported",
            entity_type="offline_session",
            entity_id=bundle.get("username", ""),
            metadata={
                "applied_actions": results["applied_actions"],
                "bundle_exported_at": bundle.get("exported_at"),
                "source_username": bundle.get("username", ""),
            },
        )
        return Response(results, status=status.HTTP_200_OK)

from __future__ import annotations

from datetime import date, timedelta
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ClientProfile, Invoice, SmsLog, SmsTemplate
from .services import (
    ANNIVERSARY_TEMPLATE_CODE,
    FORTIETH_TEMPLATE_CODE,
    calculate_invoice_totals,
    calculate_reminder_dates,
    send_sms_via_kavenegar,
)


class OperationsApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username="operator",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff)
        self.client_profile = ClientProfile.objects.create(
            full_name="خانواده رضایی",
            phone="09123456789",
            province="تهران",
            memorial_date=date(2026, 1, 10),
        )
        SmsTemplate.objects.create(code=FORTIETH_TEMPLATE_CODE, title="چهلم", body="چهلم {deceased_name}")
        SmsTemplate.objects.create(code=ANNIVERSARY_TEMPLATE_CODE, title="سالگرد", body="سالگرد {client_name}")

    def test_calculation_helpers(self):
        totals = calculate_invoice_totals(
            [
                type("Line", (), {"line_total": 300_000})(),
                type("Line", (), {"line_total": 120_000})(),
            ],
            discount_amount=20_000,
            fee_amount=15_000,
            tax_amount=5_000,
        )
        self.assertEqual(totals["subtotal_amount"], 420_000)
        self.assertEqual(totals["total_amount"], 420_000)

        reminder_dates = calculate_reminder_dates(self.client_profile.memorial_date)
        self.assertEqual(reminder_dates["fortieth_date"], date(2026, 2, 19))
        self.assertEqual(reminder_dates["anniversary_date"], date(2027, 1, 10))

    def test_staff_can_create_client(self):
        response = self.client.post(
            reverse("admin-client-list-create"),
            {
                "full_name": "مشتری جدید",
                "phone": "09111111111",
                "province": "البرز",
                "deceased_name": "مرحوم تست",
                "memorial_date": "2026-02-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["full_name"], "مشتری جدید")
        self.assertEqual(response.data["fortieth_date"], "2026-03-13")

    def test_staff_can_create_invoice_and_totals_are_recalculated(self):
        response = self.client.post(
            reverse("admin-invoice-list-create"),
            {
                "client": str(self.client_profile.id),
                "status": Invoice.Status.DRAFT,
                "discount_amount": 10_000,
                "fee_amount": 5_000,
                "tax_amount": 2_000,
                "line_items": [
                    {"description": "پک ترحیم", "quantity": 40, "unit_price": 120_000, "discount_amount": 100_000},
                    {"description": "ارسال", "quantity": 1, "unit_price": 250_000, "discount_amount": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["subtotal_amount"], 4_950_000)
        self.assertEqual(response.data["total_amount"], 4_947_000)

    def test_dashboard_summary_returns_operational_counts(self):
        Invoice.objects.create(client=self.client_profile, created_by=self.staff)
        response = self.client.get(reverse("admin-dashboard-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["clients_count"], 1)
        self.assertEqual(response.data["invoices_count"], 1)
        self.assertIn("upcoming_reminders", response.data)

    def test_desktop_bootstrap_returns_operator_payload(self):
        Invoice.objects.create(client=self.client_profile, created_by=self.staff)
        response = self.client.get(reverse("admin-desktop-bootstrap"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("server_time", response.data)
        self.assertIn("dashboard", response.data)
        self.assertIn("clients", response.data)
        self.assertIn("invoices", response.data)
        self.assertIn("reminders", response.data)
        self.assertIn("staff", response.data)
        self.assertIn("templates", response.data)
        self.assertIn("recent_audit_logs", response.data)
        self.assertEqual(len(response.data["clients"]), 1)
        self.assertEqual(len(response.data["invoices"]), 1)

    @patch("operations.views.send_sms_via_kavenegar", return_value={"raw": [{"messageid": "1001"}]})
    def test_send_reminder_creates_sms_log(self, mocked_send):
        response = self.client.post(
            reverse("admin-client-send-reminder", kwargs={"client_id": str(self.client_profile.id)}),
            {"template_code": FORTIETH_TEMPLATE_CODE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SmsLog.objects.count(), 1)
        sms_log = SmsLog.objects.first()
        self.assertEqual(sms_log.status, SmsLog.Status.SENT)
        mocked_send.assert_called_once()

    def test_dry_run_send_reminder_returns_preview_without_sending(self):
        response = self.client.post(
            reverse("admin-client-send-reminder", kwargs={"client_id": str(self.client_profile.id)}),
            {"template_code": ANNIVERSARY_TEMPLATE_CODE, "dry_run": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("preview", response.data)
        self.assertEqual(SmsLog.objects.first().status, SmsLog.Status.PENDING)

    def test_staff_can_import_portable_offline_session_bundle(self):
        bundle = {
            "bundle_format": 1,
            "session_type": "portable_offline",
            "base_url": "https://majlesyar.com",
            "username": "desktop_operator",
            "exported_at": "2026-04-15T00:00:00+00:00",
            "snapshots": {
                "dashboard": {
                    "payload": {
                        "clients_count": 1,
                        "invoices_count": 0,
                        "draft_invoices_count": 0,
                        "sms_sent_count": 0,
                        "upcoming_reminders": [],
                    },
                    "updated_at": "2026-04-15T00:00:00+00:00",
                }
            },
            "queued_actions": [
                {
                    "action_type": "save_client",
                    "created_at": "2026-04-15T00:00:00+00:00",
                    "payload": {
                        "full_name": "Portable Import",
                        "phone": "09125556666",
                        "province": "تهران",
                        "city": "تهران",
                        "address": "",
                        "email": "",
                        "deceased_name": "",
                        "memorial_date": "2026-02-01",
                        "memorial_location": "",
                        "notes": "created offline",
                        "is_active": True,
                    },
                }
            ],
        }
        upload = SimpleUploadedFile(
            "portable.majlesyar-session",
            json.dumps(bundle).encode("utf-8"),
            content_type="application/json",
        )

        response = self.client.post(
            reverse("admin-offline-session-import"),
            {"session_file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["applied_actions"], 1)
        self.assertEqual(response.data["clients_created"], 1)
        self.assertTrue(ClientProfile.objects.filter(full_name="Portable Import").exists())

    def test_client_update_returns_conflict_for_stale_sync_timestamp(self):
        stale_timestamp = (self.client_profile.updated_at - timedelta(minutes=5)).isoformat()
        response = self.client.patch(
            reverse("admin-client-detail", kwargs={"pk": str(self.client_profile.id)}),
            {
                "full_name": "Updated Too Late",
                "sync_base_updated_at": stale_timestamp,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["entity_type"], "clientprofile")
        self.assertIn("current_state", response.data)
        self.client_profile.refresh_from_db()
        self.assertEqual(self.client_profile.full_name, "خانواده رضایی")

    def test_invoice_update_returns_conflict_for_stale_sync_timestamp(self):
        invoice = Invoice.objects.create(client=self.client_profile, created_by=self.staff)
        stale_timestamp = (invoice.updated_at - timedelta(minutes=5)).isoformat()
        response = self.client.patch(
            reverse("admin-invoice-detail", kwargs={"pk": str(invoice.id)}),
            {
                "status": Invoice.Status.PAID,
                "line_items": [],
                "sync_base_updated_at": stale_timestamp,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["entity_type"], "invoice")
        self.assertIn("current_state", response.data)

    def test_seed_desktop_ui_test_data_command_creates_expected_records(self):
        call_command("clear_desktop_ui_test_data")
        call_command("seed_desktop_ui_test_data")

        user_model = get_user_model()
        self.assertTrue(user_model.objects.filter(username="desktoptester", is_staff=True).exists())
        self.assertTrue(ClientProfile.objects.filter(phone="09129990001").exists())
        self.assertTrue(Invoice.objects.filter(notes="seeded desktop ui invoice").exists())
        self.assertTrue(SmsTemplate.objects.filter(code=FORTIETH_TEMPLATE_CODE).exists())

    @override_settings(MAJLESYAR_DESKTOP_UI_TEST_MODE=True)
    def test_send_sms_uses_desktop_ui_test_mode_stub(self):
        response = send_sms_via_kavenegar(receptor="09120000000", message="test message")
        self.assertEqual(response["raw"][0]["status"], "queued")
        self.assertEqual(response["raw"][0]["messageid"], "desktop-ui-test-message-id")

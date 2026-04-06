from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Product
from orders.models import Order
from telegram_bot.models import (
    TelegramBotAuditLog,
    TelegramBotState,
    TelegramConfirmation,
    TelegramOperator,
    TelegramUpdateReceipt,
)
from telegram_bot.services.client import TelegramApiClient
from telegram_bot.services.notifications import send_new_order_notifications
from telegram_bot.services.updates import process_update


class FakeTelegramClient(TelegramApiClient):
    def __init__(self):
        self.sent_messages: list[dict] = []
        self.callback_answers: list[dict] = []
        self.edited_messages: list[dict] = []

    def send_message(self, chat_id: int, text: str, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        self.sent_messages.append(payload)
        return payload

    def answer_callback_query(self, callback_query_id: str, text: str = ""):
        payload = {"callback_query_id": callback_query_id, "text": text}
        self.callback_answers.append(payload)
        return payload

    def edit_message_reply_markup(self, chat_id: int, message_id: int, reply_markup=None):
        payload = {"chat_id": chat_id, "message_id": message_id, "reply_markup": reply_markup}
        self.edited_messages.append(payload)
        return payload


@override_settings(
    TELEGRAM_BOT={
        "ENABLED": True,
        "TOKEN": "test-token",
        "USE_WEBHOOK": True,
        "WEBHOOK_SECRET": "secret-token",
        "WEBHOOK_PATH": "api/v1/telegram/webhook/",
        "BASE_URL": "https://example.com",
        "ALLOWED_USER_IDS": [1001],
        "ALLOWED_CHAT_IDS": [2001],
        "ADMIN_ONLY": True,
        "NOTIFICATIONS_ENABLED": True,
        "CONFIRMATION_TTL_SECONDS": 600,
        "RATE_LIMIT_PER_MINUTE": 30,
    }
)
class TelegramBotTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="staff",
            password="pass12345",
            is_staff=True,
        )
        self.operator = TelegramOperator.objects.create(
            telegram_user_id=1001,
            telegram_chat_id=2001,
            username="manager",
            django_user=self.staff_user,
        )
        self.product = Product.objects.create(
            name="پک تست",
            url_slug="test-pack",
            description="desc",
            price=100000,
            event_types=["conference"],
            contents=["حلوا"],
            featured=False,
            available=True,
        )
        self.order = Order.objects.create(
            public_id="ORD-TEST123",
            customer_name="مشتری تست",
            customer_phone="09123456789",
            customer_province="تهران",
            customer_address="تهران",
            delivery_date="2030-01-10",
            delivery_window="10-12",
            payment_method="pay-later",
            total=100000,
        )
        self.fake_client = FakeTelegramClient()

    def _message_update(self, text: str, *, user_id: int = 1001, chat_id: int = 2001, update_id: int = 1) -> dict:
        return {
            "update_id": update_id,
            "message": {
                "message_id": 10,
                "text": text,
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": "Admin",
                    "username": "manager",
                },
                "chat": {"id": chat_id, "type": "private"},
            },
        }

    def _callback_update(self, data: str, *, update_id: int = 20) -> dict:
        return {
            "update_id": update_id,
            "callback_query": {
                "id": "cbq-1",
                "from": {"id": 1001, "is_bot": False, "first_name": "Admin", "username": "manager"},
                "data": data,
                "message": {
                    "message_id": 99,
                    "chat": {"id": 2001, "type": "private"},
                },
            },
        }

    def test_unauthorized_user_is_blocked(self):
        process_update(self._message_update("/ping", user_id=9999, update_id=101), source="test", client=self.fake_client)

        self.assertIn("فهرست مجاز", self.fake_client.sent_messages[0]["text"])
        self.assertTrue(
            TelegramBotAuditLog.objects.filter(status=TelegramBotAuditLog.Status.DENIED).exists()
        )

    def test_authorized_user_can_use_ping(self):
        process_update(self._message_update("/ping", update_id=102), source="test", client=self.fake_client)

        self.assertIn("pong", self.fake_client.sent_messages[0]["text"])
        self.assertTrue(
            TelegramBotAuditLog.objects.filter(command="/ping", status=TelegramBotAuditLog.Status.SUCCESS).exists()
        )

    def test_webhook_requires_secret(self):
        client = APIClient()
        response = client.post(
            "/api/v1/telegram/webhook/",
            self._message_update("/ping", update_id=103),
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_product_write_action_requires_confirmation(self):
        process_update(self._message_update(f"/feature {self.product.url_slug}", update_id=104), source="test", client=self.fake_client)

        self.product.refresh_from_db()
        self.assertFalse(self.product.featured)
        self.assertEqual(TelegramConfirmation.objects.count(), 1)
        self.assertEqual(TelegramBotAuditLog.objects.filter(status=TelegramBotAuditLog.Status.PENDING).count(), 1)

    def test_confirmed_product_write_updates_state_and_audit(self):
        process_update(self._message_update(f"/feature {self.product.url_slug}", update_id=105), source="test", client=self.fake_client)
        confirmation = TelegramConfirmation.objects.latest("created_at")

        process_update(self._callback_update(f"confirm:{confirmation.token}", update_id=106), source="test", client=self.fake_client)

        self.product.refresh_from_db()
        self.assertTrue(self.product.featured)
        confirmation.refresh_from_db()
        self.assertIsNotNone(confirmation.consumed_at)
        confirmation.audit_log.refresh_from_db()
        self.assertEqual(confirmation.audit_log.status, TelegramBotAuditLog.Status.SUCCESS)

    def test_object_not_found_is_handled_cleanly(self):
        process_update(self._message_update("/product missing-slug", update_id=107), source="test", client=self.fake_client)

        self.assertIn("محصول پیدا نشد", self.fake_client.sent_messages[0]["text"])
        self.assertTrue(
            TelegramBotAuditLog.objects.filter(command="/product", status=TelegramBotAuditLog.Status.FAILED).exists()
        )

    def test_invalid_order_status_is_blocked(self):
        process_update(self._message_update("/orderstatus ORD-TEST123 invalid", update_id=108), source="test", client=self.fake_client)
        confirmation = TelegramConfirmation.objects.latest("created_at")

        processed = process_update(
            self._callback_update(f"confirm:{confirmation.token}", update_id=109),
            source="test",
            client=self.fake_client,
        )

        self.assertFalse(processed)
        self.assertEqual(TelegramUpdateReceipt.objects.get(update_id=109).status, "failed")

    def test_duplicate_update_is_ignored(self):
        update = self._message_update("/ping", update_id=110)
        process_update(update, source="test", client=self.fake_client)
        process_update(update, source="test", client=self.fake_client)

        self.assertEqual(TelegramUpdateReceipt.objects.filter(update_id=110).count(), 1)

    def test_notification_delivery_uses_registered_operators(self):
        send_new_order_notifications(self.fake_client)

        self.assertEqual(len(self.fake_client.sent_messages), 1)
        self.assertIn("ORD-TEST123", self.fake_client.sent_messages[0]["text"])
        self.assertTrue(TelegramBotState.objects.filter(key="new_order_notifications").exists())

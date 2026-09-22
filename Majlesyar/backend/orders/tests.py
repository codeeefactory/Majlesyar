from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Product
from site_settings.models import SiteSetting

from .models import Order, OrderItem


class PublicOrderPackMinimumTests(APITestCase):
    def setUp(self):
        settings = SiteSetting.load()
        settings.min_order_qty = 40
        settings.lead_time_hours = 0
        settings.allowed_provinces = ["تهران"]
        settings.delivery_windows = ["10-12"]
        settings.payment_methods = [{"id": "pay-later", "label": "پرداخت بعد از تایید", "enabled": True}]
        settings.save()

        self.pack = Product.objects.create(
            name="پک تست",
            url_slug="public-pack-limit-test",
            public_path="/pack/public-pack-limit-test",
            price=100000,
            available=True,
        )
        self.flower = Product.objects.create(
            name="گل تست",
            url_slug="public-flower-limit-test",
            public_path="/flower/public-flower-limit-test",
            price=200000,
            available=True,
        )

    def _payload(self, items):
        return {
            "items": items,
            "customer": {
                "name": "مشتری تست",
                "phone": "09123456789",
                "province": "تهران",
                "address": "تهران، آدرس تست",
                "notes": "",
            },
            "delivery": {
                "date": (timezone.localdate() + timedelta(days=2)).isoformat(),
                "window": "10-12",
            },
            "payment_method": "pay-later",
        }

    def _product_item(self, product, quantity):
        return {
            "product_id": str(product.pk),
            "name": product.name,
            "quantity": quantity,
            "price": product.price,
        }

    def test_non_pack_product_has_no_minimum_quantity(self):
        response = self.client.post(
            reverse("order-create"),
            self._payload([self._product_item(self.flower, 1)]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_pack_product_below_minimum_is_rejected(self):
        response = self.client.post(
            reverse("order-create"),
            self._payload([self._product_item(self.pack, 39)]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("پک", str(response.data["items"][0]))

    def test_non_pack_quantity_does_not_fill_pack_minimum(self):
        response = self.client.post(
            reverse("order-create"),
            self._payload([
                self._product_item(self.pack, 39),
                self._product_item(self.flower, 100),
            ]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pack_at_minimum_is_accepted(self):
        response = self.client.post(
            reverse("order-create"),
            self._payload([self._product_item(self.pack, 40)]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_custom_pack_below_minimum_is_rejected(self):
        response = self.client.post(
            reverse("order-create"),
            self._payload([
                {
                    "product_id": None,
                    "name": "پک اختصاصی",
                    "quantity": 39,
                    "price": 100000,
                    "is_custom_pack": True,
                    "custom_config": {},
                }
            ]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminOrderApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="staff_order_admin",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff_user)
        self.product = Product.objects.create(
            name="پک تستی",
            url_slug="test-pack",
            description="desc",
            price=150000,
            event_types=["memorial"],
            contents=["حلوا"],
            featured=False,
            available=True,
        )

    def test_staff_can_create_admin_order(self):
        payload = {
            "status": Order.Status.PENDING,
            "customer_name": "خانواده حسینی",
            "customer_phone": "09123456789",
            "customer_province": "تهران",
            "customer_address": "تهران، خیابان نمونه",
            "customer_notes": "تماس قبل از ارسال",
            "delivery_date": "2030-01-10",
            "delivery_window": "10-12",
            "payment_method": "cash",
            "items": [
                {
                    "product_id": str(self.product.id),
                    "name": self.product.name,
                    "quantity": 2,
                    "price": 150000,
                }
            ],
        }

        response = self.client.post(reverse("admin-order-list"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["customer_name"], "خانواده حسینی")
        self.assertEqual(response.data["total"], 300000)
        self.assertEqual(len(response.data["items"]), 1)

    def test_staff_can_patch_admin_order_and_add_note(self):
        order = Order.objects.create(
            customer_name="مشتری تست",
            customer_phone="09120000000",
            customer_province="تهران",
            customer_address="آدرس",
            delivery_date="2030-02-01",
            delivery_window="12-15",
            payment_method="cash",
            total=100000,
        )

        patch_response = self.client.patch(
            reverse("admin-order-status-update", kwargs={"public_id": order.public_id}),
            {
                "status": Order.Status.CONFIRMED,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_province": order.customer_province,
                "customer_address": order.customer_address,
                "customer_notes": "بروزرسانی شده",
                "delivery_date": "2030-02-02",
                "delivery_window": "15-18",
                "payment_method": "card",
                "items": [{"name": "آیتم دستی", "quantity": 1, "price": 120000}],
            },
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["status"], Order.Status.CONFIRMED)
        self.assertEqual(patch_response.data["total"], 120000)

        note_response = self.client.post(
            reverse("admin-order-note-create", kwargs={"public_id": order.public_id}),
            {"note": "توسط ادمین ثبت شد"},
            format="json",
        )

        self.assertEqual(note_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(note_response.data["note"], "توسط ادمین ثبت شد")

    def test_staff_can_delete_admin_order(self):
        order = Order.objects.create(
            customer_name="مشتری حذف",
            customer_phone="09121111111",
            customer_province="تهران",
            customer_address="آدرس",
            delivery_date="2030-03-01",
            delivery_window="10-12",
            payment_method="cash",
            total=100000,
        )

        response = self.client.delete(reverse("admin-order-status-update", kwargs={"public_id": order.public_id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

    def test_staff_can_get_product_sales_report_by_date_range(self):
        april_order = self._create_order(
            customer_name="خانواده گزارش",
            customer_phone="09123334444",
            created_at=datetime(2030, 4, 2, 10, 0, tzinfo=dt_timezone.utc),
        )
        OrderItem.objects.create(
            order=april_order,
            product=self.product,
            name=self.product.name,
            quantity=3,
            price=150000,
        )

        may_order = self._create_order(
            customer_name="خانواده اردیبهشت",
            customer_phone="09125556666",
            created_at=datetime(2030, 5, 3, 9, 0, tzinfo=dt_timezone.utc),
        )
        OrderItem.objects.create(
            order=may_order,
            product=self.product,
            name=self.product.name,
            quantity=1,
            price=150000,
        )

        response = self.client.get(
            reverse("admin-product-sales-report"),
            {"date_from": "2030-04-01", "date_to": "2030-04-30"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rows_count"], 1)
        self.assertEqual(response.data["total_quantity"], 3)
        self.assertEqual(response.data["total_revenue"], 450000)
        self.assertEqual(response.data["rows"][0]["client_name"], "خانواده گزارش")

    def test_staff_can_filter_product_sales_report_by_product(self):
        second_product = Product.objects.create(
            name="پک دوم",
            url_slug="second-pack",
            description="desc",
            price=99000,
            event_types=["memorial"],
            contents=["خرما"],
            featured=False,
            available=True,
        )
        order = self._create_order(
            customer_name="خانواده پک دوم",
            customer_phone="09127778888",
            created_at=timezone.now(),
        )
        OrderItem.objects.create(order=order, product=self.product, name=self.product.name, quantity=2, price=150000)
        OrderItem.objects.create(order=order, product=second_product, name=second_product.name, quantity=5, price=99000)

        response = self.client.get(
            reverse("admin-product-sales-report"),
            {"product_id": str(second_product.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rows_count"], 1)
        self.assertEqual(response.data["product_name"], "پک دوم")
        self.assertEqual(response.data["total_quantity"], 5)
        self.assertEqual(response.data["rows"][0]["product_name"], "پک دوم")

    def _create_order(self, *, customer_name: str, customer_phone: str, created_at):
        order = Order.objects.create(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_province="تهران",
            customer_address="آدرس",
            delivery_date="2030-04-05",
            delivery_window="10-12",
            payment_method="cash",
            total=0,
        )
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        order.refresh_from_db()
        return order

from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalog.models import Product
from orders.models import Order, OrderItem
from operations.models import ClientProfile, Invoice, InvoiceLineItem, OperationsAuditLog, SmsLog, SmsTemplate
from operations.services import ANNIVERSARY_TEMPLATE_CODE, FORTIETH_TEMPLATE_CODE


class Command(BaseCommand):
    help = "Seed deterministic MajlesYar desktop UI test data."

    def handle(self, *args, **options):
        user_model = get_user_model()
        operator, _ = user_model.objects.get_or_create(
            username="desktoptester",
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "email": "desktoptester@majlesyar.local",
                "first_name": "Desktop",
                "last_name": "Tester",
            },
        )
        operator.is_staff = True
        operator.is_superuser = True
        operator.email = "desktoptester@majlesyar.local"
        operator.first_name = "Desktop"
        operator.last_name = "Tester"
        operator.set_password("Majles9876")
        operator.save()

        SmsTemplate.objects.update_or_create(
            code=FORTIETH_TEMPLATE_CODE,
            defaults={
                "title": "چهلم",
                "body": "یادآوری چهلم {deceased_name}",
                "is_active": True,
            },
        )
        SmsTemplate.objects.update_or_create(
            code=ANNIVERSARY_TEMPLATE_CODE,
            defaults={
                "title": "سالگرد",
                "body": "یادآوری سالگرد {client_name}",
                "is_active": True,
            },
        )

        primary_client, _ = ClientProfile.objects.update_or_create(
            phone="09129990001",
            defaults={
                "full_name": "خانواده خودکار",
                "email": "family.automation@example.com",
                "province": "تهران",
                "city": "تهران",
                "address": "تهران، خیابان تست، پلاک ۱",
                "deceased_name": "مرحوم تست خودکار",
                "memorial_date": date(2026, 4, 1),
                "memorial_location": "بهشت زهرا",
                "notes": "مشتری بذرگذاری‌شده برای تست دسکتاپ",
                "is_active": True,
                "created_by": operator,
            },
        )

        secondary_client, _ = ClientProfile.objects.update_or_create(
            phone="09129990002",
            defaults={
                "full_name": "خانواده رز",
                "email": "rose.family@example.com",
                "province": "البرز",
                "city": "کرج",
                "address": "کرج، خیابان گل",
                "deceased_name": "مرحوم گلزار",
                "memorial_date": date(2026, 5, 10),
                "memorial_location": "امامزاده طاهر",
                "notes": "داده دوم برای تست پیمایش",
                "is_active": True,
                "created_by": operator,
            },
        )

        invoice = Invoice.objects.filter(client=primary_client, notes="seeded desktop ui invoice").first()
        if invoice is None:
            invoice = Invoice.objects.create(
                client=primary_client,
                status=Invoice.Status.DRAFT,
                notes="seeded desktop ui invoice",
                discount_amount=10_000,
                fee_amount=5_000,
                tax_amount=2_000,
                created_by=operator,
            )
        else:
            invoice.status = Invoice.Status.DRAFT
            invoice.discount_amount = 10_000
            invoice.fee_amount = 5_000
            invoice.tax_amount = 2_000
            invoice.created_by = operator
            invoice.save()

        invoice.line_items.all().delete()
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="پک مراسم",
            quantity=1,
            unit_price=850_000,
            discount_amount=50_000,
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="گل‌آرایی",
            quantity=2,
            unit_price=450_000,
            discount_amount=0,
        )
        invoice.recalculate_totals()

        report_product, _ = Product.objects.update_or_create(
            url_slug="desktop-ui-report-product",
            defaults={
                "name": "پک گزارش فروش محصول",
                "description": "محصول نمونه برای تست گزارش فروش در اپ دسکتاپ",
                "price": 1_250_000,
                "event_types": ["memorial"],
                "contents": ["حلوا", "خرما", "گل‌آرایی"],
                "featured": False,
                "available": True,
            },
        )

        seeded_orders = [
            {
                "phone": "09129990003",
                "name": "خانواده گزارش اول",
                "province": "تهران",
                "address": "تهران، خیابان گزارش، پلاک ۱۰",
                "notes": "سفارش تست گزارش فروش محصول",
                "quantity": 1,
                "price": 1_250_000,
            },
            {
                "phone": "09129990004",
                "name": "خانواده گزارش دوم",
                "province": "البرز",
                "address": "کرج، بلوار فروش، پلاک ۲۴",
                "notes": "سفارش تست گزارش فروش محصول",
                "quantity": 2,
                "price": 1_180_000,
            },
        ]

        for order_seed in seeded_orders:
            order = Order.objects.filter(
                customer_phone=order_seed["phone"],
                customer_notes="سفارش تست گزارش فروش محصول",
            ).first()
            if order is None:
                order = Order.objects.create(
                    customer_name=order_seed["name"],
                    customer_phone=order_seed["phone"],
                    customer_province=order_seed["province"],
                    customer_address=order_seed["address"],
                    customer_notes="سفارش تست گزارش فروش محصول",
                    delivery_date=date(2026, 4, 25),
                    delivery_window="09:00-12:00",
                    payment_method="cash",
                    status=Order.Status.DELIVERED,
                    total=0,
                )
            else:
                order.customer_name = order_seed["name"]
                order.customer_province = order_seed["province"]
                order.customer_address = order_seed["address"]
                order.customer_notes = "سفارش تست گزارش فروش محصول"
                order.delivery_date = date(2026, 4, 25)
                order.delivery_window = "09:00-12:00"
                order.payment_method = "cash"
                order.status = Order.Status.DELIVERED
                order.save()

            order.items.all().delete()
            OrderItem.objects.create(
                order=order,
                product=report_product,
                name=report_product.name,
                quantity=order_seed["quantity"],
                price=order_seed["price"],
                is_custom_pack=False,
                custom_config={},
            )
            order.total = order_seed["quantity"] * order_seed["price"]
            order.save(update_fields=["total", "updated_at"])

        SmsLog.objects.get_or_create(
            client=primary_client,
            event_type=FORTIETH_TEMPLATE_CODE,
            recipient=primary_client.phone,
            body="پیش‌نمایش پیام تستی",
            defaults={
                "status": SmsLog.Status.PENDING,
                "sent_by": operator,
            },
        )

        OperationsAuditLog.objects.create(
            actor=operator,
            action="desktop_ui_seed",
            entity_type="desktop_test",
            entity_id=str(primary_client.id),
            metadata={
                "clients": [str(primary_client.id), str(secondary_client.id)],
                "invoice": str(invoice.id),
            },
        )

        self.stdout.write(self.style.SUCCESS("Desktop UI test data seeded."))

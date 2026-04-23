from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalog.models import Product
from orders.models import Order
from operations.models import ClientProfile, Invoice, OperationsAuditLog, SmsLog, SmsTemplate
from operations.services import ANNIVERSARY_TEMPLATE_CODE, FORTIETH_TEMPLATE_CODE


class Command(BaseCommand):
    help = "Clear deterministic MajlesYar desktop UI test data."

    def handle(self, *args, **options):
        ClientProfile.objects.filter(phone__in=["09129990001", "09129990002"]).delete()
        Invoice.objects.filter(notes="seeded desktop ui invoice").delete()
        SmsLog.objects.filter(
            recipient__in=["09129990001", "09129990002"],
            event_type__in=[FORTIETH_TEMPLATE_CODE, ANNIVERSARY_TEMPLATE_CODE],
        ).delete()
        Order.objects.filter(customer_phone__in=["09129990003", "09129990004"]).delete()
        Product.objects.filter(url_slug="desktop-ui-report-product").delete()
        OperationsAuditLog.objects.filter(action="desktop_ui_seed", entity_type="desktop_test").delete()
        SmsTemplate.objects.filter(code__in=[FORTIETH_TEMPLATE_CODE, ANNIVERSARY_TEMPLATE_CODE]).delete()
        get_user_model().objects.filter(username="desktoptester").delete()

        self.stdout.write(self.style.SUCCESS("Desktop UI test data cleared."))

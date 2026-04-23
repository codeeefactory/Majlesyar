from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Iterable

from django.conf import settings

from kavenegar import APIException, HTTPException, KavenegarAPI


FORTIETH_TEMPLATE_CODE = "fortieth_day"
ANNIVERSARY_TEMPLATE_CODE = "anniversary_day"

DEFAULT_TEMPLATE_BODIES = {
    FORTIETH_TEMPLATE_CODE: (
        "خانواده گرامی {client_name}،\n"
        "یادآوری چهلم مرحوم/مرحومه {deceased_name} برای تاریخ {fortieth_date} ثبت شده است.\n"
        "مجلس‌یار آماده هماهنگی پذیرایی و خدمات مراسم شماست."
    ),
    ANNIVERSARY_TEMPLATE_CODE: (
        "خانواده گرامی {client_name}،\n"
        "یادآوری سالگرد مرحوم/مرحومه {deceased_name} برای تاریخ {anniversary_date} ثبت شده است.\n"
        "در صورت نیاز به خدمات مجلس‌یار، تیم ما در کنار شماست."
    ),
}


@dataclass(frozen=True)
class InvoiceLineCalculation:
    quantity: int
    unit_price: int
    discount_amount: int = 0

    @property
    def line_total(self) -> int:
        gross = max(self.quantity, 0) * max(self.unit_price, 0)
        return max(gross - max(self.discount_amount, 0), 0)


def round_money(value: Decimal | float | int) -> int:
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_reminder_dates(memorial_date: date | None) -> dict[str, date | None]:
    if memorial_date is None:
        return {"fortieth_date": None, "anniversary_date": None}
    return {
        "fortieth_date": memorial_date + timedelta(days=40),
        "anniversary_date": memorial_date + timedelta(days=365),
    }


def calculate_invoice_totals(
    items: Iterable[InvoiceLineCalculation],
    *,
    discount_amount: int = 0,
    fee_amount: int = 0,
    tax_amount: int = 0,
) -> dict[str, int]:
    subtotal_amount = sum(item.line_total for item in items)
    discount_amount = max(discount_amount, 0)
    fee_amount = max(fee_amount, 0)
    tax_amount = max(tax_amount, 0)
    total_amount = max(subtotal_amount - discount_amount + fee_amount + tax_amount, 0)
    return {
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "fee_amount": fee_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
    }


def render_sms_body(template_body: str, client) -> str:
    reminder_dates = calculate_reminder_dates(client.memorial_date)
    context = {
        "client_name": client.full_name,
        "deceased_name": client.deceased_name or "عزیز شما",
        "memorial_date": client.memorial_date.isoformat() if client.memorial_date else "-",
        "fortieth_date": reminder_dates["fortieth_date"].isoformat()
        if reminder_dates["fortieth_date"]
        else "-",
        "anniversary_date": reminder_dates["anniversary_date"].isoformat()
        if reminder_dates["anniversary_date"]
        else "-",
    }
    return template_body.format(**context)


def resolve_kavenegar_credentials() -> tuple[str, str]:
    api_key = (getattr(settings, "KAVENEGAR_API_KEY", "") or os.getenv("KAVENEGAR_API_KEY", "")).strip()
    sender = (getattr(settings, "KAVENEGAR_SENDER", "") or os.getenv("KAVENEGAR_SENDER", "")).strip()
    return api_key, sender


def send_sms_via_kavenegar(*, receptor: str, message: str) -> dict:
    if getattr(settings, "MAJLESYAR_DESKTOP_UI_TEST_MODE", False):
        return {
            "raw": [
                {
                    "messageid": "desktop-ui-test-message-id",
                    "status": "queued",
                    "statustext": "simulated",
                    "receptor": receptor,
                    "message": message,
                }
            ]
        }

    api_key, sender = resolve_kavenegar_credentials()
    if not api_key:
        raise RuntimeError("KAVENEGAR_API_KEY is not configured.")

    client = KavenegarAPI(api_key)
    params = {
        "receptor": receptor,
        "message": message,
    }
    if sender:
        params["sender"] = sender
    try:
        response = client.sms_send(params)
    except (APIException, HTTPException) as exc:
        raise RuntimeError(str(exc)) from exc
    return {"raw": response}

from __future__ import annotations

from django import forms
from django.db import models


class PersianAdminFormMixin:
    """
    Add consistent Persian hints/notes and ensure field widgets are visible/readable.
    """

    required_label_suffix = " (الزامی)"
    optional_label_suffix = " (اختیاری)"

    class Media:
        css = {"all": ("admin/css/persian-admin-overrides.css",)}
        js = ("admin/js/clear-image-input.js",)

    placeholder_map = {
        "name": "نام را وارد کنید",
        "slug": "نمونه: economic-pack",
        "url_slug": "نمونه: vip-pack",
        "description": "توضیحات را وارد کنید",
        "event_types": 'مثال: ["conference", "memorial"]',
        "contents": 'مثال: ["آب معدنی", "میوه", "شیرینی"]',
        "image_name": "مثال: pak-terhim-luxury",
        "image_alt": "مثال: پک ترحیم کامل با بطری آب و میوه",
        "price": "مثال: 120000",
        "customer_name": "نام کامل مشتری",
        "customer_phone": "09xxxxxxxxx",
        "customer_province": "نام استان",
        "customer_address": "آدرس کامل تحویل",
        "delivery_window": "مثال: 10-12",
        "payment_method": "مثال: pay-later",
        "note": "متن یادداشت را وارد کنید",
        "full_name": "Example: Ali Ahmadi",
        "phone": "09xxxxxxxxx",
        "email": "Example: customer@example.com",
        "province": "Example: Tehran",
        "city": "Example: Tehran",
        "address": "Full delivery or customer address",
        "deceased_name": "For memorial clients",
        "memorial_location": "Example: mosque, hall, cemetery",
        "notes": "Private staff notes",
        "invoice_number": "Auto-generated",
        "discount_amount": "0",
        "fee_amount": "0",
        "tax_amount": "0",
        "subtotal_amount": "Auto-calculated",
        "total_amount": "Auto-calculated",
        "quantity": "1",
        "unit_price": "Price in toman",
        "code": "Choose template code",
        "title": "Short admin title",
        "body": "SMS text",
        "recipient": "09xxxxxxxxx",
        "provider": "kavenegar",
        "provider_message_id": "Provider delivery id",
        "provider_response": "{}",
        "error_message": "Provider error text",
        "action": "Example: invoice_created",
        "entity_type": "Example: invoice",
        "entity_id": "Related record id",
        "metadata": "{}",
    }
    help_text_map = {
        "name": "نام محصول یا آیتم را کوتاه، دقیق و قابل فهم وارد کنید.",
        "slug": "اسلاگ باید انگلیسی، یکتا و بدون فاصله باشد.",
        "url_slug": "بخش پایانی آدرس محصول را وارد کنید (فقط انگلیسی، عدد و خط تیره).",
        "description": "توضیح کامل و واضحی از محصول برای نمایش در سایت وارد کنید.",
        "categories": "دسته‌بندی‌های مرتبط با این محصول را انتخاب کنید.",
        "tags": "تگ‌های مرتبط با این محصول را انتخاب کنید.",
        "event_types": "نوع مراسم را با مقدارهای معتبر مثل conference یا memorial ثبت کنید.",
        "contents": "اقلام داخل پک را به صورت لیست ثبت کنید.",
        "image": "تصویر واضح و باکیفیت محصول را انتخاب کنید.",
        "image_name": "نام فایل تصویر را کوتاه و معنی‌دار وارد کنید.",
        "image_alt": "متن جایگزین تصویر را توصیفی و واضح وارد کنید.",
        "price": "قیمت را به تومان ثبت کنید. در صورت توافقی بودن، فیلد را خالی بگذارید.",
        "available": "اگر محصول قابل سفارش است این گزینه را فعال نگه دارید.",
        "featured": "برای نمایش محصول در بخش ویژه، این گزینه را فعال کنید.",
        "full_name": "Customer or contact full name. Use the name staff should see in invoices and follow-up.",
        "phone": "Mobile number must be reachable and usually starts with 09.",
        "email": "Optional email for customer records.",
        "province": "Delivery/follow-up province. Keep spelling consistent for filters.",
        "city": "Delivery/follow-up city.",
        "address": "Full address only when needed for delivery or customer history.",
        "deceased_name": "For memorial customers only. Leave empty for normal customers.",
        "memorial_date": "Use when reminder SMS or memorial follow-up is needed.",
        "memorial_location": "Mosque, hall, cemetery, or ceremony place if known.",
        "notes": "Private staff notes. Do not put public website copy here.",
        "is_active": "Disable only when this record should no longer be used.",
        "invoice_number": "Generated automatically when invoice is saved.",
        "client": "Customer connected to this invoice or SMS.",
        "status": "Current workflow state. Update when order/invoice/SMS progress changes.",
        "issue_date": "Date invoice is issued.",
        "due_date": "Optional payment deadline.",
        "discount_amount": "Discount in toman. Use 0 when there is no discount.",
        "fee_amount": "Extra service or delivery fee in toman. Use 0 when none.",
        "tax_amount": "Tax in toman. Use 0 when none.",
        "subtotal_amount": "Calculated subtotal before invoice-level adjustments.",
        "total_amount": "Calculated final total.",
        "quantity": "Number of this invoice/order item.",
        "unit_price": "Single item price in toman.",
        "code": "Internal template code. Pick the matching event type.",
        "title": "Short admin title. Customers may not see this.",
        "body": "Message text. Review carefully before activating.",
        "recipient": "Phone number receiving this SMS.",
        "provider": "SMS provider name. Usually leave unchanged.",
        "provider_message_id": "Delivery id returned by SMS provider.",
        "provider_response": "Raw provider response for debugging.",
        "error_message": "Reason sending failed, if provider returned one.",
        "action": "Short name of the action that happened.",
        "entity_type": "Type of record affected, like invoice or client.",
        "entity_id": "Id of the affected record.",
        "metadata": "Extra technical details in JSON format.",
    }

    def _build_placeholder(self, db_field: models.Field, label: str) -> str:
        if db_field.name in self.placeholder_map:
            return self.placeholder_map[db_field.name]

        if isinstance(db_field, (models.PositiveIntegerField, models.IntegerField)):
            return "عدد وارد کنید"
        if isinstance(db_field, models.DateField):
            return "تاریخ را انتخاب کنید"
        if isinstance(db_field, models.TextField):
            return f"{label} را وارد کنید"
        if isinstance(db_field, models.CharField):
            return f"{label} را وارد کنید"
        return ""

    def _label_with_required_state(self, label: str, required: bool) -> str:
        clean_label = (label or "").strip()
        for suffix in (self.required_label_suffix, self.optional_label_suffix):
            if clean_label.endswith(suffix):
                clean_label = clean_label[: -len(suffix)].rstrip()
        return f"{clean_label}{self.required_label_suffix if required else self.optional_label_suffix}"

    def _help_text_with_required_state(self, help_text: str, required: bool) -> str:
        state_note = "این فیلد الزامی است." if required else "این فیلد اختیاری است."
        clean_help_text = (help_text or "").strip()
        if not clean_help_text:
            return f"{state_note}"
        if clean_help_text.startswith("این فیلد الزامی است.") or clean_help_text.startswith(
            "این فیلد اختیاری است."
        ):
            return clean_help_text
        return f"{state_note} {clean_help_text}"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield is None:
            return formfield

        widget = formfield.widget
        is_required = bool(formfield.required)
        label = formfield.label or str(db_field.verbose_name)
        base_label = (label or "").strip()
        formfield.label = self._label_with_required_state(base_label, is_required)

        if hasattr(widget, "attrs"):
            widget.attrs.setdefault("dir", "rtl")
            widget.attrs.setdefault("style", "width: 100%;")
            widget.attrs["aria-required"] = "true" if is_required else "false"
            widget.attrs["data-field-required"] = "true" if is_required else "false"

            if isinstance(
                widget,
                (
                    forms.TextInput,
                    forms.Textarea,
                    forms.NumberInput,
                    forms.URLInput,
                    forms.EmailInput,
                ),
            ):
                placeholder = self._build_placeholder(db_field, base_label)
                if placeholder:
                    widget.attrs.setdefault("placeholder", placeholder)

        explicit_help_text = self.help_text_map.get(db_field.name)
        help_text = (formfield.help_text or "").strip()
        if explicit_help_text:
            formfield.help_text = explicit_help_text
        elif not help_text:
            formfield.help_text = f"نکته: مقدار «{base_label}» را دقیق وارد کنید."
        elif "نکته:" not in help_text:
            formfield.help_text = f"{help_text} | نکته: قبل از ذخیره، مقدار این فیلد را بررسی کنید."
        formfield.help_text = self._help_text_with_required_state(formfield.help_text, is_required)

        return formfield

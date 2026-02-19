from __future__ import annotations

from django import forms
from django.db import models


class PersianAdminFormMixin:
    """
    Add consistent Persian hints/notes and ensure field widgets are visible/readable.
    """

    class Media:
        css = {"all": ("admin/css/persian-admin-overrides.css",)}
        js = ("admin/js/clear-image-input.js",)

    placeholder_map = {
        "name": "نام را وارد کنید",
        "slug": "نمونه: economic-pack",
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield is None:
            return formfield

        widget = formfield.widget
        label = formfield.label or str(db_field.verbose_name)

        if hasattr(widget, "attrs"):
            widget.attrs.setdefault("dir", "rtl")
            widget.attrs.setdefault("style", "width: 100%;")

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
                placeholder = self._build_placeholder(db_field, label)
                if placeholder:
                    widget.attrs.setdefault("placeholder", placeholder)

        help_text = (formfield.help_text or "").strip()
        if not help_text:
            formfield.help_text = f"نکته: مقدار «{label}» را دقیق وارد کنید."
        elif "نکته:" not in help_text:
            formfield.help_text = f"{help_text} | نکته: قبل از ذخیره، مقدار این فیلد را بررسی کنید."

        return formfield

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    DEFAULT_EVENT_PAGES,
    DEFAULT_HOMEPAGE_BENEFITS_SECTION,
    DEFAULT_PAGE_SEO,
    DEFAULT_SITE_BRANDING,
    DEFAULT_SITE_TOP_NOTICE,
    DEFAULT_THEME_PALETTE,
    SiteSetting,
)


class SiteSettingRetrieveAPIViewTests(TestCase):
    def test_settings_endpoint_includes_branding_theme_and_dynamic_page_content(self):
        response = self.client.get("/api/v1/settings/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["site_branding"]["site_name"], DEFAULT_SITE_BRANDING["site_name"])
        self.assertEqual(payload["theme_palette"]["primary"], DEFAULT_THEME_PALETTE["primary"])
        self.assertEqual(payload["page_seo"]["home"]["title"], DEFAULT_PAGE_SEO["home"]["title"])
        self.assertEqual(payload["event_pages"][0]["slug"], DEFAULT_EVENT_PAGES[0]["slug"])
        self.assertEqual(payload["site_top_notice"]["title"], DEFAULT_SITE_TOP_NOTICE["title"])
        self.assertEqual(
            payload["homepage_benefits_section"]["title"],
            DEFAULT_HOMEPAGE_BENEFITS_SECTION["title"],
        )


class SiteSettingModelTests(TestCase):
    def test_save_normalizes_branding_theme_page_seo_and_event_pages(self):
        setting = SiteSetting.load()
        setting.site_branding = {
            "site_name": "برند نمونه",
            "default_meta_keywords": ["  کلیدواژه اول ", "", None, "کلیدواژه دوم"],
            "admin_site_symbol": "storefront",
        }
        setting.theme_palette = {
            "primary": "00c2f2",
            "foreground": "#1f2937",
            "muted_foreground": "xyz",
        }
        setting.page_seo = {
            "about": {
                "description": "توضیح سفارشی درباره ما",
                "keywords": [" درباره ما ", "مجلس یار"],
            },
            "landing": {
                "title": "فرود اختصاصی",
                "description": "متن تستی",
                "keywords": ["سفارشی"],
            },
        }
        setting.event_pages = [
            {
                "id": "custom-event",
                "name": "رویداد سفارشی",
                "slug": "custom-event",
                "description": "شرح رویداد",
                "seo_title": "رویداد سفارشی",
                "seo_description": "توضیح سفارشی",
                "seo_keywords": [" مهمانی ", "", "سفارشی"],
                "faqs": [
                    {"question": "سوال تستی", "answer": "پاسخ تستی"},
                    {"question": "", "answer": ""},
                ],
                "icon": "🎉",
                "color": "bg-accent",
                "available": False,
            }
        ]
        setting.site_top_notice = {"message": "متن سفارشی"}
        setting.homepage_benefits_section = {
            "title": "مزیت‌های سفارشی",
            "items": [
                {
                    "title": "نمونه",
                    "description": "توضیح تستی",
                    "note": "یادداشت ریز",
                }
            ],
        }

        setting.save()
        setting.refresh_from_db()

        self.assertEqual(setting.site_branding["site_name"], "برند نمونه")
        self.assertEqual(
            setting.site_branding["site_alternate_name"],
            DEFAULT_SITE_BRANDING["site_alternate_name"],
        )
        self.assertEqual(
            setting.site_branding["default_meta_keywords"],
            ["کلیدواژه اول", "کلیدواژه دوم"],
        )
        self.assertEqual(setting.theme_palette["primary"], "#00C2F2")
        self.assertEqual(setting.theme_palette["foreground"], "#1F2937")
        self.assertEqual(
            setting.theme_palette["muted_foreground"],
            DEFAULT_THEME_PALETTE["muted_foreground"],
        )
        self.assertEqual(
            setting.page_seo["about"]["title"],
            DEFAULT_PAGE_SEO["about"]["title"],
        )
        self.assertEqual(setting.page_seo["about"]["description"], "توضیح سفارشی درباره ما")
        self.assertEqual(setting.page_seo["about"]["keywords"], ["درباره ما", "مجلس یار"])
        self.assertEqual(setting.page_seo["landing"]["title"], "فرود اختصاصی")
        self.assertEqual(len(setting.event_pages), 1)
        self.assertEqual(setting.event_pages[0]["slug"], "custom-event")
        self.assertEqual(setting.event_pages[0]["seo_keywords"], ["مهمانی", "سفارشی"])
        self.assertEqual(
            setting.event_pages[0]["faqs"],
            [{"question": "سوال تستی", "answer": "پاسخ تستی"}],
        )
        self.assertFalse(setting.event_pages[0]["available"])
        self.assertEqual(setting.site_top_notice["title"], DEFAULT_SITE_TOP_NOTICE["title"])
        self.assertEqual(setting.site_top_notice["message"], "متن سفارشی")
        self.assertEqual(
            setting.homepage_benefits_section["eyebrow"],
            DEFAULT_HOMEPAGE_BENEFITS_SECTION["eyebrow"],
        )
        self.assertEqual(setting.homepage_benefits_section["title"], "مزیت‌های سفارشی")


class PingAPIViewTests(TestCase):
    def test_ping_endpoint_returns_uncached_success_payload(self):
        response = self.client.get("/api/v1/ping/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.assertIn("server_time", response.json())
        self.assertEqual(
            response.headers["Cache-Control"],
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertEqual(response.headers["Expires"], "0")


class AdminSiteSettingApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="site_admin",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff_user)

    def test_staff_can_patch_site_settings(self):
        response = self.client.patch(
            reverse("admin-site-setting-detail"),
            {
                "min_order_qty": 5,
                "lead_time_hours": 12,
                "allowed_provinces": ["تهران", "البرز"],
                "delivery_windows": [{"id": "morning", "label": "صبح"}],
                "payment_methods": [{"id": "cash", "label": "نقدی", "enabled": True}],
                "contact_phone": "02100000000",
                "contact_address": "تهران",
                "working_hours": "9-18",
                "instagram_url": "https://instagram.com/majlesyar",
                "telegram_url": "https://t.me/majlesyar",
                "whatsapp_url": "https://wa.me/989121234567",
                "bale_url": "https://ble.ir/majlesyar",
                "maps_url": "https://maps.google.com",
                "maps_embed_url": "https://maps.google.com/embed",
                "site_branding": {"site_name": "مجلس‌یار دسکتاپ"},
                "theme_palette": {"primary": "#00C2F2"},
                "page_seo": {"home": {"title": "عنوان تازه"}},
                "event_pages": [{"slug": "memorial", "name": "ترحیم"}],
                "site_top_notice": {"message": "اطلاعیه جدید"},
                "homepage_benefits_section": {"title": "مزایای تازه", "items": []},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["min_order_qty"], 5)
        self.assertEqual(response.data["contact_phone"], "02100000000")
        self.assertEqual(response.data["site_branding"]["site_name"], "مجلس‌یار دسکتاپ")

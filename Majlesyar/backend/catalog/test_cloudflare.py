from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .cloudflare import CloudflarePurgeResult, purge_cloudflare_cache, purge_cloudflare_files


class CloudflarePurgeTests(SimpleTestCase):
    @override_settings(CLOUDFLARE_API_TOKEN="secret-token", CLOUDFLARE_ZONE_ID="zone-id", MEDIA_URL="/media/")
    @patch("catalog.cloudflare.requests.post")
    def test_deleted_image_purge_uses_exact_encoded_urls(self, post_mock):
        response = Mock(ok=True, content=b"{}")
        response.json.return_value = {"success": True}
        post_mock.return_value = response

        result = purge_cloudflare_files({"products/optimized/pak/640/پک عزا.avif"})

        self.assertTrue(result.purged)
        self.assertEqual(
            post_mock.call_args.kwargs["json"],
            {"files": ["https://majlesyar.com/media/products/optimized/pak/640/%D9%BE%DA%A9%20%D8%B9%D8%B2%D8%A7.avif"]},
        )

    @override_settings(CLOUDFLARE_API_TOKEN="secret-token", CLOUDFLARE_ZONE_ID="zone-id")
    @patch("catalog.cloudflare.requests.post")
    def test_full_purge_uses_explicit_purge_everything_payload(self, post_mock):
        response = Mock(ok=True, content=b"{}")
        response.json.return_value = {"success": True}
        post_mock.return_value = response

        result = purge_cloudflare_cache()

        self.assertTrue(result.purged_everything)
        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.kwargs["json"], {"purge_everything": True})
        self.assertNotIn("secret-token", str(post_mock.call_args.kwargs["json"]))

    @override_settings(CLOUDFLARE_API_TOKEN="", CLOUDFLARE_ZONE_ID="")
    @patch("catalog.cloudflare.requests.post")
    def test_missing_credentials_returns_safe_warning_without_request(self, post_mock):
        result = purge_cloudflare_cache()

        self.assertFalse(result.attempted)
        self.assertTrue(result.error)
        post_mock.assert_not_called()

    @override_settings(CLOUDFLARE_API_TOKEN="secret-token", CLOUDFLARE_ZONE_ID="zone-id")
    @patch("catalog.cloudflare.requests.post")
    def test_failed_response_does_not_raise_or_disclose_credentials(self, post_mock):
        response = Mock(ok=False, content=b"not-json")
        response.json.side_effect = ValueError("invalid response")
        post_mock.return_value = response

        result = purge_cloudflare_cache()

        self.assertTrue(result.attempted)
        self.assertFalse(result.purged_everything)
        self.assertTrue(result.error)
        self.assertNotIn("secret-token", result.error)


class CloudflareAdminDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username="cache-admin",
            email="cache-admin@example.com",
            password="pass12345",
        )
        self.staff_user = user_model.objects.create_user(
            username="cache-staff",
            password="pass12345",
            is_staff=True,
        )

    def test_dashboard_button_is_visible_only_to_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "پاک‌سازی کش Cloudflare")

        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, "پاک‌سازی کش Cloudflare")

    def test_staff_user_cannot_purge_cache(self):
        self.client.force_login(self.staff_user)
        with patch("catalog.admin_views.purge_cloudflare_cache") as purge_mock:
            response = self.client.post(reverse("admin-cloudflare-purge"))

        self.assertEqual(response.status_code, 403)
        purge_mock.assert_not_called()

    @patch("catalog.admin_views.purge_cloudflare_cache")
    def test_superuser_can_request_purge_from_dashboard(self, purge_mock):
        purge_mock.return_value = CloudflarePurgeResult(attempted=True, purged_everything=True)
        self.client.force_login(self.superuser)

        response = self.client.post(reverse("admin-cloudflare-purge"))

        self.assertRedirects(response, reverse("admin:index"))
        purge_mock.assert_called_once_with()

    @patch("catalog.admin_views.purge_cloudflare_cache")
    def test_get_request_never_purges_cache(self, purge_mock):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin-cloudflare-purge"))

        self.assertEqual(response.status_code, 405)
        purge_mock.assert_not_called()

    @patch("catalog.admin_views.purge_cloudflare_cache")
    def test_post_without_csrf_token_never_purges_cache(self, purge_mock):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.superuser)

        response = csrf_client.post(reverse("admin-cloudflare-purge"))

        self.assertEqual(response.status_code, 403)
        purge_mock.assert_not_called()

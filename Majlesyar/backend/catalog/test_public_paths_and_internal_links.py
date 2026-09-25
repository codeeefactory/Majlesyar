from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from site_settings.models import SiteSetting

from .models import Category, InternalLink, Product, sync_product_categories


class ProductPublicPathTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_full_majlesyar_url_is_normalized_and_resolved(self):
        product = Product.objects.create(
            name="پک تست",
            url_slug="custom-pack",
            public_path="https://majlesyar.com/pack/custom-pack/",
        )

        self.assertEqual(product.public_path, "/pack/custom-pack")
        response = self.client.get(reverse("product-by-path"), {"path": product.public_path})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["uri"], "/pack/custom-pack")

    def test_legacy_malformed_majlesyar_url_is_repaired_without_data_write(self):
        product = Product.objects.create(
            name="پک همایش قدیمی",
            url_slug="legacy-conference-pack",
            public_path="/pack/conference",
        )
        Product.objects.filter(pk=product.pk).update(public_path="/https:/majlesyar.com/pack/conference")

        response = self.client.get(reverse("product-by-path"), {"path": "/pack/conference"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["public_path"], "/pack/conference")
        self.assertEqual(response.data["uri"], "/pack/conference")

    def test_external_and_legacy_product_paths_are_rejected(self):
        with self.assertRaises(ValidationError):
            Product.objects.create(name="خارجی", public_path="https://example.com/item")
        with self.assertRaises(ValidationError):
            Product.objects.create(name="قدیمی", public_path="/product/old-item")

    def test_selected_categories_replace_stale_event_types(self):
        memorial, _created = Category.objects.get_or_create(slug="memorial", defaults={"name": "ترحیم"})
        Product.objects.create(name="محصول گل", url_slug="flower-item", event_types=["party"])
        product = Product.objects.get(url_slug="flower-item")
        product.categories.set([memorial])

        sync_product_categories(product, force=True)
        product.refresh_from_db()

        self.assertEqual(product.event_types, ["memorial"])
        self.assertEqual(list(product.categories.values_list("slug", flat=True)), ["memorial"])


class ManagedInternalLinkTests(TestCase):
    def setUp(self):
        SiteSetting.load()
        InternalLink.objects.filter(source_path="/pack/memorial").delete()
        self.client = APIClient()

    def test_managed_image_link_overrides_default_card_and_exposes_alt(self):
        InternalLink.objects.create(
            source_path="/pack/memorial",
            label="پک اختصاصی من",
            target_url="/builder",
            image_alt="تصویر ساخت پک اختصاصی",
            position=1,
        )

        response = self.client.get(reverse("site-setting-detail"))
        memorial = next(page for page in response.data["event_pages"] if page["slug"] == "memorial")
        builder_link = next(link for link in memorial["internal_links"] if link["url"] == "/builder")

        self.assertEqual(builder_link["label"], "پک اختصاصی من")
        self.assertEqual(builder_link["image_alt"], "تصویر ساخت پک اختصاصی")

    def test_deleted_managed_link_does_not_return_from_hidden_fallback_data(self):
        link = InternalLink.objects.create(
            source_path="/pack/memorial",
            label="ساخت پک اختصاصی",
            target_url="/builder",
            position=1,
        )
        link.delete()

        response = self.client.get(reverse("site-setting-detail"))
        memorial = next(page for page in response.data["event_pages"] if page["slug"] == "memorial")

        self.assertNotIn("/builder", [item["url"] for item in memorial["internal_links"]])


class InternalLinkAdminTests(TestCase):
    def setUp(self):
        InternalLink.objects.all().delete()
        self.user = get_user_model().objects.create_superuser(
            username="internal-link-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.link = InternalLink.objects.create(
            source_path="/pack",
            label="پک‌های ترحیم و ختم",
            target_url="/pack/memorial",
            position=10,
        )

    def test_changelist_shows_existing_link_and_both_urls(self):
        response = self.client.get(reverse("admin:catalog_internallink_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پک‌های ترحیم و ختم")
        self.assertContains(response, "/pack")
        self.assertContains(response, "/pack/memorial")

    def test_existing_link_has_edit_and_delete_pages(self):
        change_url = reverse("admin:catalog_internallink_change", args=[self.link.pk])
        delete_url = reverse("admin:catalog_internallink_delete", args=[self.link.pk])

        self.assertEqual(self.client.get(change_url).status_code, 200)
        self.assertEqual(self.client.get(delete_url).status_code, 200)

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

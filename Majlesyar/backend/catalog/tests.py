import shutil
import tempfile
import unittest
import json
import re
from io import BytesIO
from io import StringIO
from unittest.mock import patch
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from config.admin_branding import get_admin_theme_manifest
from .image_utils import register_image_plugins
from .models import (
    BuilderItem,
    Category,
    CustomerReview,
    PageProductPlacement,
    Product,
    ProductGalleryImage,
    Tag,
    ensure_event_categories,
)
from site_settings.models import SiteSetting, get_default_event_pages


AVIF_SUPPORTED = register_image_plugins()


class AdminThemeManifestTests(APITestCase):
    def test_manifest_reflects_available_product_type_mix(self):
        settings = SiteSetting.load()
        settings.event_pages = [
            {"id": "conference", "name": "فینگر فود", "slug": "conference", "icon": "🍢", "available": True},
            {"id": "memorial", "name": "ترحیم", "slug": "memorial", "icon": "🕯️", "available": True},
            {"id": "party", "name": "گل", "slug": "party", "icon": "💐", "available": True},
        ]
        settings.save()

        Product.objects.create(
            name="فینگرفود ویژه",
            url_slug="fingerfood-special",
            description="desc",
            price=100000,
            event_types=["conference"],
            contents=[],
            available=True,
            featured=True,
        )
        Product.objects.create(
            name="گل تشریفات",
            url_slug="flowers-special",
            description="desc",
            price=100000,
            event_types=["party"],
            contents=[],
            available=True,
            featured=False,
        )
        Product.objects.create(
            name="پک ترحیم",
            url_slug="memorial-pack",
            description="desc",
            price=100000,
            event_types=["memorial"],
            contents=[],
            available=False,
            featured=False,
        )

        manifest = get_admin_theme_manifest()

        self.assertGreaterEqual(len(manifest["events"]), 3)
        event_by_slug = {event["slug"]: event for event in manifest["events"]}
        self.assertEqual(event_by_slug["conference"]["count"], 1)
        self.assertTrue(event_by_slug["conference"]["is_active"])
        self.assertEqual(event_by_slug["party"]["available_count"], 1)
        self.assertEqual(event_by_slug["memorial"]["available_count"], 0)
        self.assertIn("فینگر فود", manifest["summary"]["line"])
        self.assertIn("گل", manifest["summary"]["description"])


class AdminProductApiTests(APITestCase):
    def setUp(self):
        self.temp_media_dir = tempfile.mkdtemp(prefix="majlesyar-test-media-")
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media_dir, MEDIA_URL="/media/")
        self.media_override.enable()

        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="staff",
            password="pass12345",
            is_staff=True,
        )
        self.normal_user = user_model.objects.create_user(
            username="normal",
            password="pass12345",
            is_staff=False,
        )
        self.category_one = Category.objects.create(name="Conference", slug="conference-test", icon="C")
        self.category_two = Category.objects.create(name="Luxury", slug="luxury-test", icon="L")
        self.tag_one = Tag.objects.create(name="Popular", slug="popular-test")
        self.tag_two = Tag.objects.create(name="Ready", slug="ready-test")

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)
        super().tearDown()

    def _staff_auth(self):
        self.client.force_authenticate(user=self.staff_user)

    def _make_uploaded_image(self, name: str, image_format: str, size: tuple[int, int] = (10, 10)) -> SimpleUploadedFile:
        content_type_map = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "AVIF": "image/avif",
        }
        buffer = BytesIO()
        Image.new("RGB", size, (255, 0, 0)).save(buffer, format=image_format)
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type_map[image_format])

    def test_product_admin_renders_builder_section(self):
        self.staff_user.is_superuser = True
        self.staff_user.save(update_fields=["is_superuser"])
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("admin:catalog_product_add"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "نمایش در سازنده پک اختصاصی")
        self.assertContains(response, "تصاویر بیشتر محصول")
        self.assertContains(response, "id_show_in_builder")
        self.assertContains(response, "id_builder_group")
        self.assertContains(response, "id_builder_required")
        self.assertContains(response, "id_builder_display_order")
        self.assertContains(response, "id_is_temporary")

        from .admin import ProductAdmin

        self.assertNotIn("url_slug", ProductAdmin.prepopulated_fields)

    def test_product_detail_returns_ordered_gallery_images(self):
        product = Product.objects.create(
            name="محصول چند تصویری",
            url_slug="multi-image-product",
            description="توضیحات",
            available=True,
        )
        later = ProductGalleryImage.objects.create(
            product=product,
            image=self._make_uploaded_image("نمای دوم.jpg", "JPEG"),
            image_alt="نمای دوم محصول",
            display_order=20,
        )
        earlier = ProductGalleryImage.objects.create(
            product=product,
            image=self._make_uploaded_image("نمای اول.jpg", "JPEG"),
            image_alt="نمای اول محصول",
            display_order=10,
        )

        response = self.client.get(reverse("product-detail", args=[product.url_slug]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["gallery_images"]],
            [str(earlier.id), str(later.id)],
        )
        self.assertEqual(response.data["gallery_images"][0]["image_alt"], "نمای اول محصول")
        self.assertTrue(response.data["gallery_images"][0]["image"].startswith("http://testserver/media/"))

    @patch("catalog.cloudflare.requests.post")
    def test_product_admin_image_replacement_keeps_public_urls(self, cloudflare_post_mock):
        self.staff_user.is_superuser = True
        self.staff_user.save(update_fields=["is_superuser"])
        self.client.force_login(self.staff_user)
        product = Product.objects.create(
            name="Admin stable image URL",
            url_slug="admin-stable-image-url",
            description="Admin replacement regression",
            price=88000,
            builder_group=Product.BuilderGroup.PRODUCTS,
            builder_display_order=1,
            image=self._make_uploaded_image("original-admin-photo.jpg", "JPEG", size=(1200, 1200)),
        )
        original_image_name = product.image.name
        original_variant_paths = {
            item["path"]
            for variants in product.image_variants["variants"].values()
            for item in variants
        }
        original_backup_path = product.image_variants["original"]["backup_path"]

        response = self.client.post(
            reverse("admin:catalog_product_change", args=(product.pk,)),
            {
                "input_mode": Product.InputMode.NORMAL,
                "name": product.name,
                "url_slug": product.url_slug,
                "description": product.description,
                "price": str(product.price),
                "event_types": "[]",
                "contents": "[]",
                "image_name": product.image_name,
                "image_alt": product.image_alt,
                "available": "on",
                "show_in_builder": "on",
                "builder_group": Product.BuilderGroup.PRODUCTS,
                "builder_display_order": "1",
                "image": self._make_uploaded_image("new-admin-photo.png", "PNG", size=(1200, 1200)),
                "gallery_images-TOTAL_FORMS": "0",
                "gallery_images-INITIAL_FORMS": "0",
                "gallery_images-MIN_NUM_FORMS": "0",
                "gallery_images-MAX_NUM_FORMS": "20",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        product.refresh_from_db()
        self.assertEqual(product.image.name, original_image_name)
        self.assertEqual(product.image_variants["original"]["backup_path"], original_backup_path)
        self.assertEqual(
            {
                item["path"]
                for variants in product.image_variants["variants"].values()
                for item in variants
            },
            original_variant_paths,
        )
        with Image.open(product.image.path) as stored_image:
            self.assertEqual(stored_image.format, "JPEG")
        cloudflare_post_mock.assert_not_called()

    def test_builder_product_filter_includes_every_available_product(self):
        visible_first = Product.objects.create(
            name="Builder visible first",
            url_slug="builder-visible-first",
            price=120000,
            available=True,
            show_in_builder=True,
            builder_group=Product.BuilderGroup.FRUIT,
            builder_display_order=10,
        )
        visible_second = Product.objects.create(
            name="Builder visible second",
            url_slug="builder-visible-second",
            price=130000,
            available=True,
            show_in_builder=True,
            builder_group=Product.BuilderGroup.DRINK,
            builder_display_order=20,
        )
        hidden = Product.objects.create(
            name="Builder hidden",
            url_slug="builder-hidden",
            price=140000,
            available=True,
            show_in_builder=False,
        )
        Product.objects.create(
            name="Builder unavailable",
            url_slug="builder-unavailable",
            price=150000,
            available=False,
            show_in_builder=True,
        )
        Product.objects.create(
            name="Builder without price",
            url_slug="builder-without-price",
            price=None,
            available=True,
            show_in_builder=True,
        )

        response = self.client.get(reverse("product-list"), {"builder": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [
                str(visible_first.id),
                str(visible_second.id),
                str(hidden.id),
                str(Product.objects.get(url_slug="builder-without-price").id),
            ],
        )

        self._staff_auth()
        update_response = self.client.patch(
            reverse("admin-product-detail", args=(hidden.id,)),
            {
                "show_in_builder": True,
                "builder_group": Product.BuilderGroup.SNACK,
                "builder_display_order": 5,
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=None)

        enabled_response = self.client.get(reverse("product-list"), {"builder": "true"})

        self.assertEqual(enabled_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in enabled_response.data],
            [
                str(hidden.id),
                str(visible_first.id),
                str(visible_second.id),
                str(Product.objects.get(url_slug="builder-without-price").id),
            ],
        )
        self.assertIn("no-store", enabled_response.headers["Cache-Control"])

    def test_staff_created_product_is_available_in_builder_feed(self):
        self._staff_auth()
        response = self.client.post(
            reverse("admin-product-list-create"),
            {
                "name": "محصول تازه برای سازنده",
                "url_slug": "fresh-builder-product",
                "description": "محصولی که از پنل مدیریت ثبت شده است.",
                "price": "175000",
                "available": "true",
                "show_in_builder": "true",
                "builder_group": "products",
                "builder_display_order": "3",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(user=None)

        builder_response = self.client.get(reverse("product-list"), {"builder": "true"})

        self.assertEqual(builder_response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data["id"], [item["id"] for item in builder_response.data])

    def test_staff_can_create_product_using_frontend_payload_shape(self):
        self._staff_auth()
        payload = {
            "name": "محصول تست",
            "url_slug": "mahsol-test",
            "description": "توضیحات",
            "price": 123000,
            "category_ids": [str(self.category_one.id), str(self.category_two.id)],
            "tag_ids": [str(self.tag_one.id), str(self.tag_two.id)],
            "event_types": ["conference", "party"],
            "contents": ["آیتم 1", "آیتم 2"],
            "image": "/placeholder.svg",
            "featured": True,
            "available": True,
            "is_temporary": True,
            "show_in_builder": True,
            "builder_group": "snack",
            "builder_required": True,
            "builder_display_order": 12,
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["url_slug"], payload["url_slug"])
        self.assertTrue(set(payload["category_ids"]).issubset(set(response.data["category_ids"])))
        self.assertCountEqual(response.data["tag_ids"], payload["tag_ids"])

        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.price, payload["price"])
        self.assertTrue(created.is_temporary)
        self.assertTrue(created.show_in_builder)
        self.assertEqual(created.builder_group, "snack")
        self.assertTrue(created.builder_required)
        self.assertEqual(created.builder_display_order, 12)
        self.assertTrue(response.data["show_in_builder"])
        self.assertTrue(response.data["is_temporary"])
        self.assertEqual(response.data["builder_group"], "snack")
        self.assertTrue(response.data["builder_required"])
        self.assertEqual(response.data["builder_display_order"], 12)
        self.assertEqual(
            response.data["contents"],
            [{"name": "آیتم 1", "price": None}, {"name": "آیتم 2", "price": None}],
        )
        self.assertTrue(
            {self.category_one.id, self.category_two.id}.issubset(
                set(created.categories.values_list("id", flat=True))
            )
        )
        self.assertCountEqual(
            list(created.tags.values_list("id", flat=True)),
            [self.tag_one.id, self.tag_two.id],
        )

    def test_temporary_product_detail_sets_crawler_header(self):
        product = Product.objects.create(
            name="Temporary crawler test",
            url_slug="temporary-crawler-test",
            description="Temporary product",
            available=True,
            is_temporary=True,
        )

        response = self.client.get(reverse("product-detail", args=[product.url_slug]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_temporary"])
        self.assertEqual(
            response.headers["X-Robots-Tag"],
            "noindex, nofollow, noarchive, nosnippet",
        )

    def test_staff_can_create_product_contents_with_item_prices(self):
        self._staff_auth()
        payload = {
            "name": "پک قیمت‌دار",
            "url_slug": "priced-pack",
            "description": "توضیحات",
            "price": 200000,
            "category_ids": [str(self.category_one.id)],
            "event_types": ["conference"],
            "contents": [
                {"name": "آبمیوه", "price": 25000},
                {"name": "کیک", "price": None},
            ],
            "featured": False,
            "available": True,
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["contents"], payload["contents"])
        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.contents, payload["contents"])

    def test_staff_can_patch_product_categories_and_flags(self):
        self._staff_auth()
        product = Product.objects.create(
            name="Old product",
            description="desc",
            price=10000,
            event_types=["conference"],
            contents=["item"],
            featured=False,
            available=True,
        )
        product.categories.set([self.category_one])
        product.tags.set([self.tag_one])

        payload = {
            "name": "Updated product",
            "url_slug": "updated-product",
            "category_ids": [str(self.category_two.id)],
            "tag_ids": [str(self.tag_two.id)],
            "available": False,
            "featured": True,
            "show_in_builder": False,
            "builder_group": "addon",
            "builder_required": False,
            "builder_display_order": 7,
            "image": None,
        }
        url = reverse("admin-product-detail", kwargs={"id": str(product.id)})
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated product")
        self.assertEqual(response.data["url_slug"], "updated-product")
        self.assertIn(str(self.category_two.id), response.data["category_ids"])
        self.assertCountEqual(response.data["tag_ids"], [str(self.tag_two.id)])
        self.assertFalse(response.data["available"])
        self.assertTrue(response.data["featured"])
        self.assertFalse(response.data["show_in_builder"])
        self.assertEqual(response.data["builder_group"], "addon")
        self.assertFalse(response.data["builder_required"])
        self.assertEqual(response.data["builder_display_order"], 7)

    def test_staff_can_delete_product(self):
        self._staff_auth()
        product = Product.objects.create(
            name="Delete product",
            description="desc",
            price=10000,
            event_types=[],
            contents=[],
        )
        url = reverse("admin-product-detail", kwargs={"id": str(product.id)})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=product.id).exists())

    def test_non_staff_cannot_create_product(self):
        self.client.force_authenticate(user=self.normal_user)
        payload = {
            "name": "محصول",
            "category_ids": [str(self.category_one.id)],
            "event_types": [],
            "contents": [],
            "featured": False,
            "available": True,
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_product_detail_supports_lookup_by_url_slug_and_uuid(self):
        product = Product.objects.create(
            name="Public Product",
            url_slug="public-product",
            description="desc",
            price=10000,
            event_types=["conference"],
            contents=["item"],
        )
        product.categories.set([self.category_one])
        product.tags.set([self.tag_one])

        by_slug = self.client.get(reverse("product-detail", kwargs={"lookup": "public-product"}))
        self.assertEqual(by_slug.status_code, status.HTTP_200_OK)
        self.assertEqual(by_slug.data["id"], str(product.id))
        self.assertEqual(by_slug.data["url_slug"], "public-product")

        by_uuid = self.client.get(reverse("product-detail", kwargs={"lookup": str(product.id)}))
        self.assertEqual(by_uuid.status_code, status.HTTP_200_OK)
        self.assertEqual(by_uuid.data["id"], str(product.id))
        self.assertEqual(by_uuid.data["url_slug"], "public-product")

    def test_public_product_detail_includes_approved_customer_reviews(self):
        product = Product.objects.create(
            name="Reviewed Product",
            url_slug="reviewed-product",
            description="desc",
            price=10000,
            event_types=["conference"],
            contents=["item"],
        )
        CustomerReview.objects.create(
            product=product,
            customer_name="سارا",
            customer_city="تهران",
            title="کیفیت عالی",
            comment="همه چیز مرتب و تازه بود.",
            rating=5,
            is_approved=True,
            is_featured=True,
        )
        CustomerReview.objects.create(
            product=product,
            customer_name="مخفی",
            comment="نمایش داده نشود",
            rating=3,
            is_approved=False,
        )

        response = self.client.get(reverse("product-detail", kwargs={"lookup": "reviewed-product"}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["customer_reviews"]), 1)
        self.assertEqual(response.data["customer_reviews"][0]["customer_name"], "سارا")
        self.assertEqual(response.data["customer_reviews"][0]["rating"], 5)

    def test_public_reviews_endpoint_filters_unapproved_reviews(self):
        product = Product.objects.create(
            name="Public Review Product",
            description="desc",
            price=10000,
            event_types=["conference"],
            contents=[],
        )
        CustomerReview.objects.create(
            product=product,
            customer_name="علی",
            comment="تحویل دقیق بود.",
            rating=4,
            is_approved=True,
            is_featured=True,
        )
        CustomerReview.objects.create(
            product=product,
            customer_name="رد شده",
            comment="نباید بیاید",
            rating=1,
            is_approved=False,
            is_featured=True,
        )

        response = self.client.get(reverse("customer-review-list"), {"featured": "true", "limit": "6"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["customer_name"], "علی")

    def test_staff_can_create_customer_review(self):
        self._staff_auth()
        product = Product.objects.create(
            name="Admin Review Product",
            description="desc",
            price=10000,
            event_types=["conference"],
            contents=[],
        )

        response = self.client.post(
            reverse("admin-customer-review-list-create"),
            {
                "product": str(product.id),
                "customer_name": "مینا",
                "customer_city": "کرج",
                "title": "پیشنهاد می‌کنم",
                "comment": "برای مراسم ما بسیار خوب بود.",
                "rating": 5,
                "is_approved": True,
                "is_featured": True,
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomerReview.objects.count(), 1)
        created = CustomerReview.objects.get()
        self.assertEqual(created.product, product)
        self.assertEqual(created.rating, 5)

    def test_staff_can_create_product_with_png_and_derived_image_metadata(self):
        self._staff_auth()
        payload = {
            "name": "محصول تصویری",
            "description": "توضیحات",
            "price": "123000",
            "event_types": ["conference"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("majlesyar-pack.png", "PNG"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["image_name"], "majlesyar pack")
        self.assertEqual(response.data["image_alt"], "majlesyar pack")

        created = Product.objects.get(id=response.data["id"])
        self.assertTrue(created.image.name.endswith(".png"))
        self.assertEqual(created.image_name, "majlesyar pack")
        self.assertEqual(created.image_alt, "majlesyar pack")

        self.assertTrue(created.image.storage.exists(created.image.name))

    def test_staff_can_upload_utf8_image_without_storage_suffix_noise(self):
        self._staff_auth()
        payload = {
            "name": "محصول با عکس فارسی",
            "description": "توضیحات",
            "price": "123000",
            "event_types": ["party"],
            "contents": ["گل"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("دسته گل ویژه.jpg", "JPEG"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        image_stem = Path(created.image.name).stem
        self.assertEqual(Path(created.image.name).name, "دسته گل ویژه.jpg")
        self.assertEqual(image_stem, "دسته گل ویژه")
        self.assertIsNone(re.search(r"_[A-Za-z0-9]{7}$", image_stem))
        self.assertEqual(created.image_name, "دسته گل ویژه")
        self.assertEqual(created.image_alt, "دسته گل ویژه")
        self.assertTrue(created.image.storage.exists(created.image.name))
        backup_name = created.image_variants["original"]["backup_path"].split("/")[-1]
        self.assertEqual(backup_name, "دسته گل ویژه.jpg")

    def test_staff_can_create_product_with_webp_image(self):
        self._staff_auth()
        payload = {
            "name": "محصول وب‌پی",
            "description": "توضیحات",
            "price": "456000",
            "event_types": ["memorial"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("funeral-pack.webp", "WEBP"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertTrue(created.image.name.endswith(".webp"))
        self.assertEqual(created.image_name, "funeral pack")
        self.assertEqual(created.image_alt, "funeral pack")

        self.assertTrue(created.image.storage.exists(created.image.name))

    def test_replacing_product_image_keeps_all_public_image_urls(self):
        self._staff_auth()
        create_response = self.client.post(
            reverse("admin-product-list-create"),
            {
                "name": "محصول با آدرس تصویر ثابت",
                "url_slug": "stable-image-urls",
                "description": "توضیحات",
                "price": "456000",
                "image_file": self._make_uploaded_image("original-photo.jpg", "JPEG", size=(1200, 1200)),
            },
            format="multipart",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(id=create_response.data["id"])
        original_storage_name = product.image.name
        original_signature = product.image_variants["signature"]

        def public_urls(payload):
            responsive = payload["image_responsive"]
            urls = {payload["image"], responsive["backup_url"], responsive["fallback"]["src"]}
            for variants in responsive["formats"].values():
                urls.update(item["url"] for item in variants)
            return urls

        urls_before = public_urls(create_response.data)
        replacement_buffer = BytesIO()
        Image.new("RGB", (1200, 1200), (0, 128, 0)).save(replacement_buffer, format="PNG")
        replacement = SimpleUploadedFile(
            "completely-new-name.png",
            replacement_buffer.getvalue(),
            content_type="image/png",
        )

        update_response = self.client.patch(
            reverse("admin-product-detail", kwargs={"id": str(product.id)}),
            {"image_file": replacement},
            format="multipart",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.image.name, original_storage_name)
        self.assertNotEqual(product.image_variants["signature"], original_signature)
        self.assertEqual(public_urls(update_response.data), urls_before)
        with Image.open(product.image.path) as stored_image:
            self.assertEqual(stored_image.format, "JPEG")

    def test_product_upload_dir_uses_slug_not_uuid(self):
        self._staff_auth()
        payload = {
            "name": "پک ترحیم 4",
            "description": "توضیحات",
            "price": "123000",
            "event_types": ["memorial"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("پک_ترحیم_4.jpg", "JPEG"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        relative_path = Path(created.image.name)
        self.assertEqual(relative_path.parent.name, "پک-ترحیم-4")
        self.assertNotEqual(relative_path.parent.name, str(created.id))
        self.assertTrue(created.image.storage.exists(created.image.name))

    def test_product_upload_dir_prefers_stable_url_slug(self):
        self._staff_auth()
        payload = {
            "name": "پک ترحیم قابل اشتراک",
            "url_slug": "memorial-pack-shareable",
            "description": "توضیحات",
            "price": "123000",
            "event_types": ["memorial"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("پک_ترحیم_قابل_اشتراک.jpg", "JPEG"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        relative_path = Path(created.image.name)
        self.assertEqual(relative_path.parent.name, "memorial-pack-shareable")
        self.assertEqual(relative_path.name, "پک_ترحیم_قابل_اشتراک.jpg")

    def test_product_upload_generates_responsive_variants_and_backup(self):
        self._staff_auth()
        payload = {
            "name": "دسته گل بهینه",
            "description": "توضیحات",
            "price": "456000",
            "event_types": ["party"],
            "contents": ["گل"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("daste-gol-optimized.jpg", "JPEG", size=(1400, 1400)),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        metadata = created.image_variants
        self.assertTrue(metadata)
        self.assertEqual(metadata["original"]["width"], 1400)
        self.assertEqual(metadata["original"]["height"], 1400)
        self.assertTrue(created.image.storage.exists(metadata["original"]["backup_path"]))
        self.assertEqual(
            [item["width"] for item in metadata["variants"]["jpeg"]],
            [320, 384, 480, 640, 768, 960, 1280],
        )
        self.assertTrue(all(created.image.storage.exists(item["path"]) for item in metadata["variants"]["webp"]))
        self.assertTrue(response.data["image_responsive"]["fallback"]["src"])
        self.assertEqual(response.data["image_responsive"]["width"], 1400)
        self.assertEqual(response.data["image_alt"], created.image_alt)

    def test_product_upload_center_crops_responsive_variants_to_square(self):
        self._staff_auth()
        payload = {
            "name": "تصویر افقی محصول",
            "description": "توضیحات",
            "price": "456000",
            "event_types": ["party"],
            "contents": ["گل"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image(
                "landscape-product.jpg",
                "JPEG",
                size=(1200, 800),
            ),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        metadata = created.image_variants
        self.assertEqual(metadata["original"]["width"], 1200)
        self.assertEqual(metadata["original"]["height"], 800)
        self.assertEqual(metadata["display"]["width"], 800)
        self.assertEqual(metadata["display"]["height"], 800)
        self.assertEqual(metadata["display"]["aspect_ratio"], "1:1")
        for variants in metadata["variants"].values():
            self.assertTrue(all(item["width"] == item["height"] for item in variants))
        self.assertEqual(response.data["image_responsive"]["width"], 800)
        self.assertEqual(response.data["image_responsive"]["height"], 800)

    def test_regenerate_product_image_variants_command_processes_existing_images(self):
        product = Product.objects.create(
            name="گل تازه",
            url_slug="fresh-flowers",
            description="محصول تصویری",
            price=150000,
            event_types=["party"],
            contents=["گل"],
            image=self._make_uploaded_image("fresh-flowers.jpg", "JPEG", size=(1400, 1400)),
        )
        Product.objects.filter(pk=product.pk).update(image_variants={})

        output = StringIO()
        call_command(
            "regenerate_product_image_variants",
            "--product",
            product.url_slug,
            stdout=output,
        )

        product.refresh_from_db()
        self.assertTrue(product.image_variants["variants"]["jpeg"])
        self.assertIn("Image optimization summary", output.getvalue())

    @unittest.skipUnless(AVIF_SUPPORTED, "AVIF plugin is not installed in this environment.")
    def test_staff_can_create_product_with_avif_image(self):
        self._staff_auth()
        payload = {
            "name": "محصول آویف",
            "description": "توضیحات",
            "price": "456000",
            "event_types": ["memorial"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("funeral-pack.avif", "AVIF"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertTrue(created.image.name.endswith(".avif"))
        self.assertEqual(created.image_name, "funeral pack")
        self.assertEqual(created.image_alt, "funeral pack")

        self.assertTrue(created.image.storage.exists(created.image.name))

    def test_manual_image_alt_remains_editable(self):
        self._staff_auth()
        payload = {
            "name": "محصول با آلت اختصاصی",
            "description": "توضیحات",
            "price": "789000",
            "event_types": ["conference"],
            "contents": ["آیتم 1"],
            "featured": "false",
            "available": "true",
            "image_alt": "متن جایگزین دلخواه",
            "image_file": self._make_uploaded_image("custom-alt.webp", "WEBP"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["image_alt"], "متن جایگزین دلخواه")

        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.image_alt, "متن جایگزین دلخواه")
        self.assertEqual(created.image_name, "custom alt")

    def test_product_event_categories_are_auto_added_when_missing(self):
        self._staff_auth()
        auto_category, _ = Category.objects.get_or_create(
            slug="halva-khorma",
            defaults={"name": "حلوا و خرما", "icon": "🍯"},
        )
        payload = {
            "name": "پک حلوا و خرما",
            "description": "حلوا و خرما برای مراسم",
            "price": 100000,
            "event_types": ["halva-khorma"],
            "contents": ["حلوا", "خرما"],
            "featured": False,
            "available": True,
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertIn(auto_category.id, created.categories.values_list("id", flat=True))
        self.assertEqual(created.event_types, ["halva-khorma"])

    def test_existing_event_category_backfills_event_types(self):
        auto_category, _ = Category.objects.get_or_create(
            slug="halva-khorma",
            defaults={"name": "حلوا و خرما", "icon": "🍯"},
        )
        product = Product.objects.create(
            name="محصول حلوا",
            description="مناسب مراسم",
            price=100000,
            event_types=[],
            contents=["حلوا"],
        )
        product.categories.set([auto_category])

        product.save()
        product.refresh_from_db()

        self.assertEqual(product.event_types, ["halva-khorma"])

    @patch(
        "catalog.models.analyze_product_image",
        return_value={
            "success": True,
            "detections": [
                {"label": "خرما", "label_key": "date", "confidence": 0.94},
                {"label": "حلوا", "label_key": "halva", "confidence": 0.81},
            ],
            "top_label": "خرما",
            "top_label_key": "date",
            "uncertain": False,
            "error": None,
            "threshold": 0.72,
            "model_version": "test-model",
        },
    )
    def test_photo_processing_mode_detects_contents(self, mocked_analyze):
        self._staff_auth()
        payload = {
            "name": "پک تشخیص تصویر",
            "description": "بدون محتوا",
            "price": "99000",
            "input_mode": "photo_processing",
            "event_types": [],
            "contents": [],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("halva-khorma.webp", "WEBP"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.contents, [{"name": "خرما", "price": None}, {"name": "حلوا", "price": None}])
        self.assertEqual(created.photo_analysis["top_label"], "خرما")
        mocked_analyze.assert_called_once()

    @unittest.skipUnless(AVIF_SUPPORTED, "AVIF plugin is not installed in this environment.")
    @patch(
        "catalog.models.analyze_product_image",
        return_value={
            "success": True,
            "detections": [
                {"label": "خرما", "label_key": "date", "confidence": 0.94},
            ],
            "top_label": "خرما",
            "top_label_key": "date",
            "uncertain": False,
            "error": None,
            "threshold": 0.72,
            "model_version": "test-model",
        },
    )
    def test_photo_processing_mode_accepts_avif_image(self, mocked_analyze):
        self._staff_auth()
        payload = {
            "name": "پک تشخیص آویف",
            "description": "بدون محتوا",
            "price": "99000",
            "input_mode": "photo_processing",
            "event_types": [],
            "contents": [],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("halva-khorma.avif", "AVIF"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.photo_analysis["top_label"], "خرما")
        mocked_analyze.assert_called_once()

    @patch("catalog.models.analyze_product_image")
    def test_normal_mode_does_not_detect_contents_from_image(self, mocked_analyze):
        self._staff_auth()
        payload = {
            "name": "پک عادی",
            "description": "بدون محتوا",
            "price": "99000",
            "input_mode": "normal",
            "event_types": [],
            "contents": [],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("halva-khorma.webp", "WEBP"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.contents, [])
        self.assertEqual(created.photo_analysis, {})
        mocked_analyze.assert_not_called()

    def test_rejects_corrupt_uploaded_image(self):
        self._staff_auth()
        bad_file = SimpleUploadedFile("broken.jpg", b"not-an-image", content_type="image/jpeg")
        payload = {
            "name": "تصویر خراب",
            "description": "توضیحات",
            "price": "50000",
            "event_types": [],
            "contents": [],
            "image_file": bad_file,
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_file", response.data)

    @patch(
        "catalog.models.analyze_product_image",
        return_value={
            "success": False,
            "detections": [],
            "top_label": None,
            "top_label_key": None,
            "uncertain": True,
            "error": "model_unavailable",
            "threshold": 0.72,
            "model_version": None,
        },
    )
    def test_photo_processing_handles_missing_model_gracefully(self, mocked_analyze):
        self._staff_auth()
        payload = {
            "name": "پک بدون مدل",
            "description": "بدون محتوا",
            "price": "99000",
            "input_mode": "photo_processing",
            "event_types": [],
            "contents": [],
            "featured": "false",
            "available": "true",
            "image_file": self._make_uploaded_image("missing-model.jpg", "JPEG"),
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.contents, [])
        self.assertTrue(created.photo_analysis["uncertain"])
        self.assertEqual(created.photo_analysis["error"], "model_unavailable")
        mocked_analyze.assert_called_once()


class AdminCatalogSupportApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="catalog_admin",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff_user)

    def test_staff_can_create_update_and_delete_category(self):
        create_response = self.client.post(
            reverse("admin-category-list-create"),
            {
                "name": "گل ترحیم",
                "slug": "funeral-flowers",
                "icon": "F",
                "color": "#00C2F2",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        category_id = create_response.data["id"]

        patch_response = self.client.patch(
            reverse("admin-category-detail", kwargs={"id": category_id}),
            {
                "name": "گل ترحیم ویژه",
                "slug": "funeral-flowers-premium",
                "icon": "FP",
                "color": "#0F766E",
            },
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["name"], "گل ترحیم ویژه")

        delete_response = self.client.delete(reverse("admin-category-detail", kwargs={"id": category_id}))

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=category_id).exists())

    def test_staff_can_create_update_and_delete_tag(self):
        create_response = self.client.post(
            reverse("admin-tag-list-create"),
            {
                "name": "ارسال فوری",
                "slug": "fast-delivery",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        tag_id = create_response.data["id"]

        patch_response = self.client.patch(
            reverse("admin-tag-detail", kwargs={"id": tag_id}),
            {
                "name": "ارسال فوق سریع",
                "slug": "ultra-fast-delivery",
            },
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["slug"], "ultra-fast-delivery")

        delete_response = self.client.delete(reverse("admin-tag-detail", kwargs={"id": tag_id}))

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag_id).exists())

    def test_staff_can_create_update_and_delete_builder_item(self):
        create_response = self.client.post(
            reverse("admin-builder-item-list-create"),
            {
                "name": "ظرف میوه",
                "group": BuilderItem.Group.PACKAGING,
                "price": 45000,
                "required": True,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        builder_item_id = create_response.data["id"]

        patch_response = self.client.patch(
            reverse("admin-builder-item-detail", kwargs={"id": builder_item_id}),
            {
                "name": "ظرف میوه بزرگ",
                "group": BuilderItem.Group.ADDON,
                "price": 65000,
                "required": False,
            },
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data["group"], BuilderItem.Group.ADDON)
        self.assertEqual(patch_response.data["price"], 65000)
        self.assertFalse(patch_response.data["required"])

        delete_response = self.client.delete(
            reverse("admin-builder-item-detail", kwargs={"id": builder_item_id})
        )

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BuilderItem.objects.filter(id=builder_item_id).exists())


class PageProductOrderingApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="page_admin",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.staff_user)

        settings = SiteSetting.load()
        settings.event_pages = [
            {
                "id": "memorial",
                "name": "ترحیم",
                "slug": "memorial",
                "description": "صفحه محصولات ترحیم",
                "available": True,
            }
        ]
        settings.save()

        self.home_a = Product.objects.create(
            name="پک ویژه الف",
            url_slug="home-a",
            description="محصول اول",
            price=150000,
            featured=True,
            available=True,
            event_types=["memorial"],
            contents=[],
        )
        self.home_b = Product.objects.create(
            name="پک ویژه ب",
            url_slug="home-b",
            description="محصول دوم",
            price=170000,
            featured=True,
            available=True,
            event_types=["memorial"],
            contents=[],
        )
        self.home_c = Product.objects.create(
            name="پک ویژه ج",
            url_slug="home-c",
            description="محصول سوم",
            price=190000,
            featured=True,
            available=True,
            event_types=["memorial"],
            contents=[],
        )

    def test_admin_targets_include_home_and_event_pages(self):
        response = self.client.get(reverse("admin-page-product-targets"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        page_keys = {item["page_key"] for item in response.data}
        self.assertIn("home", page_keys)
        self.assertNotIn("shop", page_keys)
        self.assertIn("event:memorial", page_keys)
        self.assertIn("event:bouquets", page_keys)
        self.assertIn("event:food-charcuterie-board", page_keys)

    def test_event_categories_cover_default_frontend_pages(self):
        ensure_event_categories()
        settings = SiteSetting.load()
        category_slugs = set(Category.objects.values_list("slug", flat=True))
        event_slugs = {page["slug"] for page in settings.event_pages}

        self.assertTrue(event_slugs.issubset(category_slugs))

    def test_seed_categories_cover_default_frontend_pages(self):
        seed_path = Path(__file__).resolve().parents[1] / "seed" / "initial_data.json"
        seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
        seed_category_slugs = {item["slug"] for item in seed_payload.get("categories", [])}
        event_slugs = {page["slug"] for page in get_default_event_pages()}

        self.assertTrue(event_slugs.issubset(seed_category_slugs))

    def test_frontend_event_constants_match_backend_default_pages(self):
        frontend_path = Path(__file__).resolve().parents[2] / "src" / "data" / "siteConstants.ts"
        frontend_source = frontend_path.read_text(encoding="utf-8-sig")
        event_body = re.search(
            r"export const eventTypes: EventType\[\] = \[(.*)\]\.map\(withPdfFaqs\);",
            frontend_source,
            re.S,
        )
        self.assertIsNotNone(event_body)
        frontend_slugs = set(re.findall(r'\bslug:\s*["\']([^"\']+)["\']', event_body.group(1)))
        frontend_slugs.update(re.findall(r'hiddenEventPage\(\s*["\']([^"\']+)["\']', event_body.group(1)))
        backend_slugs = {page["slug"] for page in get_default_event_pages()}

        self.assertEqual(frontend_slugs, backend_slugs)
        self.assertNotIn('id: "defense"', frontend_source)
        self.assertRegex(
            frontend_source,
            r'id:\s*"congratulatory-wreaths",[\s\S]*?routePath:\s*"/flower/congratulatory-wreaths"',
        )
        self.assertRegex(
            frontend_source,
            r'hiddenEventPage\(\s*"flower-congratulation-wreaths",[\s\S]*?"/flower/congratulation-wreaths"',
        )

    def test_product_admin_category_autofill_covers_default_event_pages(self):
        from .admin import ProductAdmin

        event_slugs = {page["slug"] for page in get_default_event_pages()}
        admin_event_slugs = set(ProductAdmin.EVENT_CATEGORY_SLUGS)

        self.assertTrue(event_slugs.issubset(admin_event_slugs))

    def test_child_event_preview_only_uses_exact_page_category(self):
        flower_product = Product.objects.create(
            name="دسته گل تست",
            url_slug="test-bouquet",
            description="محصول گل",
            price=250000,
            featured=False,
            available=True,
            event_types=["bouquets"],
            contents=[],
        )
        unrelated_flower_product = Product.objects.create(
            name="محصول عمومی گل",
            url_slug="generic-flower",
            price=200000,
            available=True,
            event_types=["party"],
        )

        response = self.client.get(
            reverse("page-product-preview"),
            {"page_type": "event", "page_slug": "bouquets"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_ids = [item["id"] for item in response.data["products"]]
        self.assertIn(str(flower_product.id), product_ids)
        self.assertNotIn(str(unrelated_flower_product.id), product_ids)

    def test_admin_state_returns_preview_products_for_selected_page(self):
        response = self.client.get(
            reverse("admin-page-product-placements"),
            {"page_type": "home", "page_slug": "featured"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["page_key"], "home")
        self.assertFalse(response.data["uses_custom_order"])
        preview_ids = [item["id"] for item in response.data["preview_products"]]
        self.assertEqual(preview_ids, [str(self.home_a.id), str(self.home_b.id), str(self.home_c.id)])

    def test_reorder_persists_and_public_preview_reflects_saved_order(self):
        reorder_response = self.client.post(
            reverse("admin-page-product-placements-reorder"),
            {
                "page_type": "home",
                "page_slug": "featured",
                "product_ids": [str(self.home_c.id), str(self.home_a.id)],
            },
            format="json",
        )

        self.assertEqual(reorder_response.status_code, status.HTTP_200_OK)
        self.assertTrue(reorder_response.data["uses_custom_order"])
        self.assertEqual(
            [item["product_id"] for item in reorder_response.data["placements"]],
            [str(self.home_c.id), str(self.home_a.id)],
        )
        self.assertEqual(
            [item["id"] for item in reorder_response.data["preview_products"]],
            [str(self.home_c.id), str(self.home_a.id)],
        )

        placements = list(
            PageProductPlacement.objects.filter(page_type="home", page_slug="featured").order_by("position")
        )
        self.assertEqual([str(item.product_id) for item in placements], [str(self.home_c.id), str(self.home_a.id)])

        preview_response = self.client.get(
            reverse("page-product-preview"),
            {"page_type": "home", "page_slug": "featured"},
        )

        self.assertEqual(preview_response.status_code, status.HTTP_200_OK)
        self.assertTrue(preview_response.data["uses_custom_order"])
        self.assertEqual(
            [item["id"] for item in preview_response.data["products"]],
            [str(self.home_c.id), str(self.home_a.id)],
        )

    def test_shop_preview_target_is_removed(self):
        reorder_response = self.client.post(
            reverse("admin-page-product-placements-reorder"),
            {
                "page_type": "shop",
                "page_slug": "listing",
                "product_ids": [str(self.home_b.id)],
            },
            format="json",
        )

        self.assertEqual(reorder_response.status_code, status.HTTP_400_BAD_REQUEST)

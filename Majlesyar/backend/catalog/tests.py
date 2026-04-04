import shutil
import tempfile
from io import BytesIO
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Product, Tag


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

    def _make_uploaded_image(self, name: str, image_format: str) -> SimpleUploadedFile:
        content_type_map = {
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        buffer = BytesIO()
        Image.new("RGB", (10, 10), (255, 0, 0)).save(buffer, format=image_format)
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type_map[image_format])

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
        }

        response = self.client.post(reverse("admin-product-list-create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["url_slug"], payload["url_slug"])
        self.assertCountEqual(response.data["category_ids"], payload["category_ids"])
        self.assertCountEqual(response.data["tag_ids"], payload["tag_ids"])

        created = Product.objects.get(id=response.data["id"])
        self.assertEqual(created.price, payload["price"])
        self.assertCountEqual(
            list(created.categories.values_list("id", flat=True)),
            [self.category_one.id, self.category_two.id],
        )
        self.assertCountEqual(
            list(created.tags.values_list("id", flat=True)),
            [self.tag_one.id, self.tag_two.id],
        )

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
            "image": None,
        }
        url = reverse("admin-product-detail", kwargs={"id": str(product.id)})
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated product")
        self.assertEqual(response.data["url_slug"], "updated-product")
        self.assertCountEqual(response.data["category_ids"], [str(self.category_two.id)])
        self.assertCountEqual(response.data["tag_ids"], [str(self.tag_two.id)])
        self.assertFalse(response.data["available"])
        self.assertTrue(response.data["featured"])

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

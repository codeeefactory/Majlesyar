from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Product, Tag
from .product_bundle import (
    BUNDLE_CONTENT_TYPE,
    MANIFEST_NAME,
    ProductBundleError,
    export_product_bundle,
    import_product_bundle,
)


class ProductImageNameAndBundleTests(TestCase):
    def setUp(self):
        super().setUp()
        self.temp_media_dir = tempfile.mkdtemp(prefix="majlesyar-product-bundle-")
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media_dir)
        self.media_override.enable()
        self.user = get_user_model().objects.create_superuser(
            username="bundle-admin",
            email="bundle@example.com",
            password="bundle-test-password",
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(
            name="دسته آزمایشی",
            slug="bundle-test-category",
            icon="",
            color="#123456",
        )
        self.tag = Tag.objects.create(name="تگ آزمایشی", slug="bundle-test-tag")

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)
        super().tearDown()

    @staticmethod
    def image_upload(name: str = "پک 1.png", color=(20, 80, 140)) -> SimpleUploadedFile:
        output = BytesIO()
        Image.new("RGB", (24, 16), color).save(output, format="PNG")
        return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")

    def make_product(self, *, name="محصول پشتیبان", slug="portable-product", image_name="پک 1.png") -> Product:
        product = Product.objects.create(
            name=name,
            url_slug=slug,
            description="توضیح محصول پشتیبان",
            price=425000,
            event_types=["custom-event"],
            contents=[{"name": "آیتم اول", "price": 25000}],
            image=self.image_upload(image_name),
            image_alt="تصویر محصول پشتیبان",
            featured=True,
            available=True,
            is_temporary=False,
            show_in_builder=True,
            builder_group=Product.BuilderGroup.SNACK,
            builder_required=False,
            builder_display_order=17,
        )
        product.categories.set([self.category])
        product.tags.set([self.tag])
        return product

    def test_uploaded_unicode_basename_is_preserved_exactly(self):
        first = self.make_product()
        second = self.make_product(name="محصول دوم", slug="portable-product-2")

        self.assertEqual(Path(first.image.name).name, "پک 1.png")
        self.assertEqual(Path(second.image.name).name, "پک 1.png")
        self.assertNotEqual(Path(first.image.name).parent, Path(second.image.name).parent)
        self.assertTrue(unquote(first.image.url).endswith("/products/portable-product/پک 1.png"))
        self.assertTrue(unquote(second.image.url).endswith("/products/portable-product-2/پک 1.png"))
        self.assertTrue(first.image.storage.exists(first.image.name))
        self.assertTrue(second.image.storage.exists(second.image.name))
        for format_name, variants in first.image_variants["variants"].items():
            expected_extension = "jpg" if format_name == "jpeg" else format_name
            self.assertTrue(all(Path(item["path"]).name == f"پک 1.{expected_extension}" for item in variants))
            self.assertTrue(all("products/optimized/portable-product/" in item["path"] for item in variants))

    def test_normalization_command_moves_legacy_suffix_without_deleting_image(self):
        image_bytes = self.image_upload("legacy.png").read()
        legacy_name = "products/پک_قدیمی_AbC1234.png"
        Product._meta.get_field("image").storage.save(legacy_name, ContentFile(image_bytes))
        product = Product.objects.create(
            name="محصول قدیمی",
            url_slug="legacy-product",
            image=legacy_name,
            image_name="پک قدیمی AbC1234",
            image_alt="پک قدیمی AbC1234",
        )

        dry_run = StringIO()
        call_command("normalize_product_image_names", "--product", product.url_slug, stdout=dry_run)
        product.refresh_from_db()
        self.assertEqual(product.image.name, legacy_name)
        self.assertIn("dry-run", dry_run.getvalue())

        call_command("normalize_product_image_names", "--apply", "--product", product.url_slug)
        product.refresh_from_db()
        self.assertEqual(product.image.name, "products/legacy-product/پک_قدیمی.png")
        self.assertEqual(product.image_name, "پک قدیمی")
        self.assertEqual(product.image_alt, "پک قدیمی")
        self.assertTrue(product.image.storage.exists(product.image.name))
        self.assertFalse(product.image.storage.exists(legacy_name))
        self.assertTrue(product.image_variants)

    def test_normalization_command_removes_stale_uuid_media_trees(self):
        product = self.make_product()
        storage = Product._meta.get_field("image").storage
        legacy_original_dir = f"products/{product.pk}"
        legacy_optimized_dir = f"products/optimized/{product.pk}/640"
        legacy_backup_dir = f"products/originals/{product.pk}/legacy"
        image_bytes = self.image_upload("legacy-stale.jpg").read()
        storage.save(f"{legacy_original_dir}/legacy-stale.jpg", ContentFile(image_bytes))
        storage.save(f"{legacy_optimized_dir}/legacy-stale.jpg", ContentFile(image_bytes))
        storage.save(f"{legacy_backup_dir}/legacy-stale.jpg", ContentFile(image_bytes))

        call_command("normalize_product_image_names", "--apply", "--product", product.url_slug)

        self.assertFalse(storage.exists(f"{legacy_original_dir}/legacy-stale.jpg"))
        self.assertFalse(storage.exists(f"{legacy_optimized_dir}/legacy-stale.jpg"))
        self.assertFalse(storage.exists(f"{legacy_backup_dir}/legacy-stale.jpg"))

    def test_admin_export_and_import_round_trip_product(self):
        source = self.make_product()
        export_url = reverse("admin:catalog_product_export_mjlsyar", args=(source.pk,))

        response = self.client.get(export_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], BUNDLE_CONTENT_TYPE)
        self.assertIn(".mjlsyar", response.headers["Content-Disposition"])
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertIn("no-store", response.headers["Cache-Control"])

        upload = SimpleUploadedFile(
            "product.mjlsyar",
            response.content,
            content_type=BUNDLE_CONTENT_TYPE,
        )
        import_response = self.client.post(
            reverse("admin:catalog_product_import_mjlsyar"),
            {"product_bundle": upload},
        )

        self.assertEqual(import_response.status_code, 302)
        imported = Product.objects.exclude(pk=source.pk).get(name=source.name)
        self.assertEqual(imported.url_slug, f"{source.url_slug}-2")
        self.assertEqual(imported.price, source.price)
        self.assertEqual(imported.contents, source.contents)
        self.assertEqual(imported.builder_group, source.builder_group)
        self.assertEqual(set(imported.categories.values_list("slug", flat=True)), {self.category.slug})
        self.assertEqual(set(imported.tags.values_list("slug", flat=True)), {self.tag.slug})
        self.assertEqual(Path(imported.image.name).name, "پک 1.png")
        self.assertEqual(Path(imported.image.name).parent.as_posix(), "products/portable-product-2")
        with source.image.open("rb") as source_image, imported.image.open("rb") as imported_image:
            self.assertEqual(imported_image.read(), source_image.read())

    def test_bundle_rejects_image_hash_tampering_without_creating_product(self):
        source = self.make_product()
        valid_bundle = export_product_bundle(source)
        rewritten = BytesIO()
        with ZipFile(BytesIO(valid_bundle), "r") as incoming, ZipFile(
            rewritten,
            "w",
            compression=ZIP_DEFLATED,
        ) as outgoing:
            manifest = json.loads(incoming.read(MANIFEST_NAME))
            manifest["image"]["sha256"] = hashlib.sha256(b"wrong").hexdigest()
            for info in incoming.infolist():
                data = json.dumps(manifest, ensure_ascii=False).encode("utf-8") if info.filename == MANIFEST_NAME else incoming.read(info)
                outgoing.writestr(info.filename, data)

        before_count = Product.objects.count()
        with self.assertRaisesRegex(ProductBundleError, "هش تصویر"):
            import_product_bundle(rewritten.getvalue())
        self.assertEqual(Product.objects.count(), before_count)

    def test_bundle_rejects_unknown_archive_entry(self):
        source = self.make_product()
        valid_bundle = export_product_bundle(source)
        rewritten = BytesIO()
        with ZipFile(BytesIO(valid_bundle), "r") as incoming, ZipFile(
            rewritten,
            "w",
            compression=ZIP_DEFLATED,
        ) as outgoing:
            for info in incoming.infolist():
                outgoing.writestr(info.filename, incoming.read(info))
            outgoing.writestr("../outside.txt", b"not allowed")

        with self.assertRaises(ProductBundleError):
            import_product_bundle(rewritten.getvalue())

    def test_admin_pages_show_bundle_controls(self):
        product = self.make_product()

        list_response = self.client.get(reverse("admin:catalog_product_changelist"))
        change_response = self.client.get(reverse("admin:catalog_product_change", args=(product.pk,)))
        import_response = self.client.get(reverse("admin:catalog_product_import_mjlsyar"))

        self.assertContains(list_response, "افزودن از فایل .mjlsyar")
        self.assertContains(change_response, "دریافت پشتیبان .mjlsyar")
        self.assertContains(import_response, "بازیابی یک محصول")

    def test_non_staff_cannot_access_bundle_admin_views(self):
        source = self.make_product()
        ordinary_user = get_user_model().objects.create_user(
            username="ordinary-bundle-user",
            password="ordinary-password",
        )
        self.client.force_login(ordinary_user)

        export_response = self.client.get(
            reverse("admin:catalog_product_export_mjlsyar", args=(source.pk,))
        )
        import_response = self.client.get(reverse("admin:catalog_product_import_mjlsyar"))

        self.assertEqual(export_response.status_code, 302)
        self.assertEqual(import_response.status_code, 302)

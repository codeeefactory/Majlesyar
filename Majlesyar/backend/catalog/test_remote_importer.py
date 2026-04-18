from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from catalog.remote_importer import (
    ProductNameEntry,
    RemoteCatalogSnapshot,
    RemoteCategory,
    RemoteProduct,
    RemoteTag,
    build_image_alt_text,
    build_import_candidates,
    build_product_description,
    build_uploaded_image_filename,
    extract_remote_image_filename,
    infer_category_slugs,
    match_existing_products_to_images,
    match_images_to_names,
    parse_name_line,
)


class RemoteImporterHelperTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="majlesyar-importer-tests-"))
        self.images_dir = self.temp_dir / "images"
        self.images_dir.mkdir()
        (self.images_dir / "pack-1.jpg").write_bytes(b"fake")
        (self.images_dir / "luxury-pack-2.webp").write_bytes(b"fake")

        self.snapshot = RemoteCatalogSnapshot(
            categories={
                "memorial": RemoteCategory(id="cat-1", name="ترحیم", slug="memorial"),
                "luxury": RemoteCategory(id="cat-2", name="لوکس", slug="luxury"),
                "empty": RemoteCategory(id="cat-3", name="پک خالی", slug="empty"),
                "halva-khorma": RemoteCategory(id="cat-4", name="حلوا و خرما", slug="halva-khorma"),
            },
            tags={
                "vip": RemoteTag(id="tag-1", name="ویژه", slug="vip"),
                "ready-pack": RemoteTag(id="tag-2", name="پک آماده", slug="ready-pack"),
            },
            products=[
                RemoteProduct(id="prod-1", name="محصول موجود", url_slug="existing-product"),
            ],
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().tearDown()

    def test_parse_name_line_supports_filename_mapping(self):
        entry = parse_name_line("pack-1.jpg|پک ختم 1", line_number=1)

        self.assertEqual(entry.product_name, "پک ختم 1")
        self.assertEqual(entry.image_key, "pack 1 jpg")

    def test_match_images_to_names_accepts_filename_mapping(self):
        name_entries = [
            ProductNameEntry(product_name="پک ختم 1", image_key="pack 1 jpg"),
            ProductNameEntry(product_name="پک لوکس 2", image_key="luxury pack 2 webp"),
        ]

        matches = match_images_to_names(
            sorted(self.images_dir.iterdir()),
            name_entries,
            images_dir=self.images_dir,
        )

        self.assertEqual(
            [(path.name, product_name) for path, product_name in matches],
            [
                ("luxury-pack-2.webp", "پک لوکس 2"),
                ("pack-1.jpg", "پک ختم 1"),
            ],
        )

    def test_build_image_alt_text_uses_detected_contents(self):
        alt_text = build_image_alt_text(
            "پک ترحیم لوکس",
            category_names=["ترحیم"],
            contents=["خرما", "حلوا", "آبمیوه", "کیک"],
        )

        self.assertEqual(alt_text, "تصویر پک ترحیم لوکس شامل خرما، حلوا، آبمیوه")

    def test_build_product_description_mentions_category_when_contents_missing(self):
        description = build_product_description(
            "پک لوکس",
            category_names=["لوکس"],
            contents=[],
        )

        self.assertIn("پک لوکس", description)
        self.assertIn("لوکس", description)
        self.assertIn("مجلس", description)

    def test_infer_category_slugs_uses_remote_aliases_and_event_detection(self):
        category_slugs = infer_category_slugs(
            "پک ترحیم لوکس",
            image_path=self.images_dir / "luxury-pack-2.webp",
            available_categories=self.snapshot.categories,
            contents=["خرما", "حلوا"],
        )

        self.assertEqual(category_slugs, ["memorial", "halva-khorma", "luxury"])

    def test_build_import_candidates_derives_alt_text_categories_and_tags(self):
        names_file = self.temp_dir / "names.txt"
        names_file.write_text(
            "\n".join(
                [
                    "pack-1.jpg|پک ترحیم آماده",
                    "luxury-pack-2.webp|پک لوکس ترحیم",
                ]
            ),
            encoding="utf-8",
        )

        with self.settings(
            VISION_ENABLED=False,
            VISION_MODEL_PATH="",
        ):
            candidates = build_import_candidates(
                images_dir=self.images_dir,
                name_file=names_file,
                snapshot=self.snapshot,
                default_tag_slugs=["vip"],
                featured=True,
                available=True,
                price=250000,
            )

        self.assertEqual(len(candidates), 2)

        first = candidates[0]
        self.assertEqual(first.name, "پک لوکس ترحیم")
        self.assertEqual(first.price, 250000)
        self.assertTrue(first.featured)
        self.assertIn("memorial", first.category_slugs)
        self.assertIn("luxury", first.category_slugs)
        self.assertIn("vip", first.tag_slugs)
        self.assertEqual(first.image_alt, "تصویر پک لوکس ترحیم مناسب ترحیم")
        self.assertEqual(first.contents, [])

    def test_match_existing_products_to_images_uses_remote_product_name(self):
        product_image = self.images_dir / "پک ترحیم 1.webp"
        product_image.write_bytes(b"replacement")

        products = [
            RemoteProduct(
                id="prod-1",
                name="پک ترحیم 1",
                url_slug="memorial-pack-1",
                uri="/product/memorial-pack-1",
                image="https://example.com/media/products/%D9%BE%DA%A9_%D8%AA%D8%B1%D8%AD%DB%8C%D9%85_1.jpg",
                image_name="پک ترحیم 1",
                image_alt="پک ترحیم 1",
            ),
            RemoteProduct(
                id="prod-2",
                name="دسته گل 1",
                url_slug="flower-bouquet-1",
            ),
        ]

        matches, unmatched = match_existing_products_to_images(
            [product_image],
            products,
            images_dir=self.images_dir,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].product.id, "prod-1")
        self.assertEqual(matches[0].matched_key, "پک ترحیم 1")
        self.assertEqual(unmatched, [])

    def test_build_uploaded_image_filename_preserves_remote_stem(self):
        product = RemoteProduct(
            id="prod-1",
            name="پک ترحیم 2",
            url_slug="memorial-pack-2",
            image="https://example.com/media/products/%D9%BE%DA%A9_%D8%AA%D8%B1%D8%AD%DB%8C%D9%85_2.jpg",
        )

        upload_name = build_uploaded_image_filename(
            product,
            self.images_dir / "پک ترحیم 2.webp",
        )

        self.assertEqual(upload_name, "پک_ترحیم_2.webp")
        self.assertEqual(extract_remote_image_filename(product.image), "پک_ترحیم_2.jpg")

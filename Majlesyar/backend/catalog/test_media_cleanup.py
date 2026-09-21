from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.views.static import serve
from PIL import Image

from .image_variants import _all_variant_paths
from .models import Product


def image_upload(name: str, *, size: int = 1400) -> SimpleUploadedFile:
    output = BytesIO()
    Image.new("RGB", (size, size), "#9d7348").save(output, format="JPEG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/jpeg")


class ProductImageDeletionTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory(prefix="majlesyar-delete-images-")
        self.override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            MEDIA_URL="/media/",
            CLOUDFLARE_API_TOKEN="",
            CLOUDFLARE_ZONE_ID="",
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.media_directory.cleanup()

    def test_deleting_product_removes_original_and_all_responsive_widths(self):
        product = Product.objects.create(
            name="پک حذف‌شدنی",
            url_slug="deleted-product",
            image=image_upload("deleted-product.jpg"),
        )
        paths = {product.image.name, *_all_variant_paths(product.image_variants)}
        widths = {
            item["width"]
            for variants in product.image_variants["variants"].values()
            for item in variants
        }
        self.assertTrue({320, 640, 960}.issubset(widths))
        self.assertTrue(all(default_storage.exists(path) for path in paths))
        stale_path = "products/optimized/deleted-product/old/640/stale.jpg"
        default_storage.save(stale_path, ContentFile(b"stale"))
        sample_path = next(path for path in paths if "/640/" in path)
        request = RequestFactory().get(f"/media/{sample_path}")
        response = serve(request, sample_path, document_root=self.media_directory.name)
        self.assertEqual(response.status_code, 200)
        response.close()

        with patch("catalog.cloudflare.purge_cloudflare_files") as purge_mock:
            with self.captureOnCommitCallbacks(execute=True):
                Product.objects.filter(pk=product.pk).delete()

        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertTrue(all(not default_storage.exists(path) for path in paths))
        self.assertFalse(default_storage.exists(stale_path))
        self.assertIn(stale_path, purge_mock.call_args.args[0])
        with self.assertRaises(Http404):
            serve(request, sample_path, document_root=self.media_directory.name)

    def test_deleting_one_product_preserves_another_products_shared_directory(self):
        first = Product.objects.create(name="محصول مشترک", image=image_upload("first.jpg", size=320))
        second = Product.objects.create(name="محصول مشترک", image=image_upload("second.jpg", size=320))
        first_paths = {first.image.name, *_all_variant_paths(first.image_variants)}
        second_paths = {second.image.name, *_all_variant_paths(second.image_variants)}
        self.assertTrue(all(default_storage.exists(path) for path in second_paths))

        with self.captureOnCommitCallbacks(execute=True):
            first.delete()

        self.assertTrue(all(not default_storage.exists(path) for path in first_paths - second_paths))
        self.assertTrue(all(default_storage.exists(path) for path in second_paths))

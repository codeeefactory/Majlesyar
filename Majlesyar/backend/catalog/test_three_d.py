import io
import shutil
import tempfile
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Product
from .three_d import generate_asset_3d, validate_glb_file


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, format="PNG")
    return output.getvalue()


class GlbValidationTests(TestCase):
    def test_rejects_non_glb_payload(self):
        upload = SimpleUploadedFile("fake.glb", b"not-a-glb")
        with self.assertRaises(ValidationError):
            validate_glb_file(upload)


class Product3DGenerationTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp(prefix="majlesyar-3d-test-")
        self.override = override_settings(
            MEDIA_ROOT=self.media_dir,
            PRODUCT_3D_GENERATOR_URL="https://worker.invalid/generate",
            PRODUCT_3D_GENERATOR_TOKEN="secret",
            PRODUCT_3D_MAX_BYTES=1024,
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_dir, ignore_errors=True)

    def test_saves_valid_worker_glb_and_metadata(self):
        product = Product.objects.create(
            name="Test 3D product",
            url_slug="test-3d-product",
            image=SimpleUploadedFile("product.png", make_png(), content_type="image/png"),
        )
        response = Mock()
        response.iter_content.return_value = [b"glTF", b"-binary-model"]
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response

        metadata = generate_asset_3d(product, session=session)

        product.refresh_from_db()
        self.assertEqual(product.model_3d_status, "ready")
        self.assertTrue(product.model_3d.name.endswith(".glb"))
        self.assertEqual(metadata["bytes"], 17)
        self.assertEqual(session.post.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    def test_invalid_worker_payload_records_failure(self):
        product = Product.objects.create(
            name="Broken 3D product",
            url_slug="broken-3d-product",
            image=SimpleUploadedFile("product.png", make_png(), content_type="image/png"),
        )
        response = Mock()
        response.iter_content.return_value = [b"html error"]
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response

        with self.assertRaises(ValidationError):
            generate_asset_3d(product, session=session)

        product.refresh_from_db()
        self.assertEqual(product.model_3d_status, "failed")
        self.assertTrue(product.model_3d_error)

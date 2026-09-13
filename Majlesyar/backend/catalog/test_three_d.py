import io
import hashlib
import json
import shutil
import struct
import tempfile
from pathlib import Path
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from .models import Product
from .three_d import generate_asset_3d, validate_glb_bytes, validate_glb_file


def make_png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, format="PNG")
    return output.getvalue()


def make_glb() -> bytes:
    document = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": 4}],
        "bufferViews": [{"buffer": 0, "byteLength": 4}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 1, "type": "SCALAR"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
    }
    json_chunk = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_chunk += b" " * (-len(json_chunk) % 4)
    binary_chunk = b"\0\0\0\0"
    length = 12 + 8 + len(json_chunk) + 8 + len(binary_chunk)
    return b"".join(
        (
            struct.pack("<4sII", b"glTF", 2, length),
            struct.pack("<II", len(json_chunk), 0x4E4F534A),
            json_chunk,
            struct.pack("<II", len(binary_chunk), 0x004E4942),
            binary_chunk,
        )
    )


class GlbValidationTests(TestCase):
    def test_rejects_non_glb_payload(self):
        upload = SimpleUploadedFile("fake.glb", b"not-a-glb")
        with self.assertRaises(ValidationError):
            validate_glb_file(upload)

    def test_accepts_glb_with_mesh_geometry(self):
        document = validate_glb_bytes(make_glb())
        self.assertEqual(len(document["meshes"]), 1)

    def test_rejects_magic_only_payload(self):
        with self.assertRaises(ValidationError):
            validate_glb_bytes(b"glTF-binary-model")


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
        glb = make_glb()
        response.iter_content.return_value = [glb]
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response

        metadata = generate_asset_3d(product, session=session)

        product.refresh_from_db()
        self.assertEqual(product.model_3d_status, "ready")
        self.assertTrue(product.model_3d.name.endswith(".glb"))
        self.assertEqual(metadata["bytes"], len(glb))
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


class Product3DImportTests(TestCase):
    def test_imports_verified_batch_artifact(self):
        product = Product.objects.create(name="Imported model", url_slug="imported-model")
        glb = make_glb()
        digest = hashlib.sha256(glb).hexdigest()

        with tempfile.TemporaryDirectory(prefix="majlesyar-3d-artifact-") as artifact_dir, tempfile.TemporaryDirectory(
            prefix="majlesyar-3d-media-"
        ) as media_dir, override_settings(MEDIA_ROOT=media_dir):
            root = Path(artifact_dir)
            relative_path = Path("models") / "products" / f"{product.pk}.glb"
            model_path = root / relative_path
            model_path.parent.mkdir(parents=True)
            model_path.write_bytes(glb)
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "generator": "triposr",
                        "total": 1,
                        "ready": 1,
                        "failed": 0,
                        "products": [
                            {
                                "id": str(product.pk),
                                "status": "ready",
                                "model_path": relative_path.as_posix(),
                                "bytes": len(glb),
                                "sha256": digest,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            call_command("import_product_3d_models", root)
            product.refresh_from_db()

            self.assertEqual(product.model_3d_status, "ready")
            self.assertEqual(product.model_3d_metadata["sha256"], digest)
            self.assertTrue(Path(product.model_3d.path).exists())

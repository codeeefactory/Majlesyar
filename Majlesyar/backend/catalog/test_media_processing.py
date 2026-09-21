import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .media_processing import enqueue_asset_processing, process_next_asset_job
from .models import AssetProcessingJob, BuilderItem, Product


def image_upload(name: str = "asset.png", color: str = "white") -> SimpleUploadedFile:
    output = io.BytesIO()
    Image.new("RGB", (48, 48), color).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class AssetProcessingQueueTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.mkdtemp(prefix="majlesyar-media-jobs-")
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_dir,
            PRODUCT_IMAGE_ANALYZER_URL="https://worker.invalid/analyze",
            PRODUCT_3D_GENERATOR_URL="https://worker.invalid/generate",
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_dir, ignore_errors=True)

    def test_product_job_records_declared_pack_item_analysis(self):
        product = Product.objects.create(
            name="Memorial pack",
            url_slug="media-job-product",
            contents=[{"name": "خرما", "price": 12000}, {"name": "موز", "price": 9000}],
            image=image_upload(),
        )
        job = enqueue_asset_processing("product", product.pk, image_changed=True)

        self.assertIsNotNone(job)
        self.assertEqual(job.status, AssetProcessingJob.Status.PENDING)
        self.assertEqual(job.requested_actions, ["analyze", "generate_3d"])

        remote_result = {
            "success": True,
            "detections": [
                {"label_key": "date", "label": "خرما", "confidence": 0.91},
            ],
            "model_version": "clip-test",
        }
        with patch("catalog.media_processing._remote_analyze", return_value=remote_result), patch(
            "catalog.media_processing.generate_asset_3d",
            return_value={"generator": "test", "source_image_sha256": job.source_sha256},
        ):
            processed = process_next_asset_job()

        product.refresh_from_db()
        processed.refresh_from_db()
        self.assertEqual(processed.status, AssetProcessingJob.Status.SUCCEEDED)
        self.assertEqual(product.photo_analysis["source_image_sha256"], job.source_sha256)
        self.assertTrue(product.photo_analysis["training_candidate"])
        self.assertEqual(product.photo_analysis["pack_items"][0]["name"], "خرما")
        self.assertTrue(product.photo_analysis["pack_items"][0]["detected"])
        self.assertFalse(product.photo_analysis["pack_items"][1]["detected"])

    def test_new_backend_upload_is_queued_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            product = Product.objects.create(
                name="Automatic queue",
                url_slug="automatic-queue",
                image=image_upload("automatic.png"),
            )

        job = AssetProcessingJob.objects.get(target_type="product", target_id=product.pk)
        product.refresh_from_db()
        self.assertEqual(job.status, AssetProcessingJob.Status.PENDING)
        self.assertEqual(product.model_3d_status, "queued")

    def test_builder_item_image_is_analyzed_and_saved(self):
        item = BuilderItem.objects.create(
            name="آبمیوه",
            group=BuilderItem.Group.DRINK,
            price=25000,
            image=image_upload("juice.png", "orange"),
        )
        job = enqueue_asset_processing("builder_item", item.pk, image_changed=True)
        remote_result = {
            "success": True,
            "detections": [{"label_key": "juice", "label": "آبمیوه", "confidence": 0.88}],
        }

        with patch("catalog.media_processing._remote_analyze", return_value=remote_result), patch(
            "catalog.media_processing.generate_asset_3d",
            return_value={"generator": "test"},
        ):
            process_next_asset_job()

        item.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, AssetProcessingJob.Status.SUCCEEDED)
        self.assertEqual(item.photo_analysis["pack_items"][0]["name"], "آبمیوه")
        self.assertTrue(item.photo_analysis["pack_items"][0]["detected"])

    @override_settings(PRODUCT_IMAGE_ANALYZER_URL="")
    def test_missing_trained_model_falls_back_to_zero_shot_analysis(self):
        item = BuilderItem.objects.create(
            name="موز",
            group=BuilderItem.Group.FRUIT,
            price=15000,
            image=image_upload("banana.png", "yellow"),
        )
        job = enqueue_asset_processing("builder_item", item.pk, image_changed=True)
        unavailable = {"success": False, "detections": [], "error": "model_unavailable"}
        zero_shot = {
            "success": True,
            "detections": [{"label_key": "banana", "label": "موز", "confidence": 0.82}],
            "provider": "zero_shot_cpu",
        }

        with patch("catalog.media_processing.analyze_product_image", return_value=unavailable), patch(
            "catalog.media_processing._zero_shot_analyze", return_value=zero_shot
        ) as zero_shot_mock, patch("catalog.media_processing.generate_asset_3d", return_value={}):
            process_next_asset_job()

        item.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, AssetProcessingJob.Status.SUCCEEDED)
        self.assertEqual(item.photo_analysis["provider"], "zero_shot_cpu")
        self.assertTrue(item.photo_analysis["pack_items"][0]["detected"])
        zero_shot_mock.assert_called_once()

    def test_removed_image_cancels_pending_work(self):
        product = Product.objects.create(
            name="Removed image",
            url_slug="removed-image",
            image=image_upload(),
        )
        job = enqueue_asset_processing("product", product.pk, image_changed=True)
        product.image.delete(save=False)
        Product.objects.filter(pk=product.pk).update(image=None)

        result = enqueue_asset_processing("product", product.pk, image_changed=True)

        job.refresh_from_db()
        product.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(job.status, AssetProcessingJob.Status.SKIPPED)
        self.assertEqual(product.model_3d_status, "missing")

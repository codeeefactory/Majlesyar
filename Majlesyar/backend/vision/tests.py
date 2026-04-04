from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from PIL import Image

from vision.service import normalize_prediction, predict_products


class VisionServiceTests(SimpleTestCase):
    def _make_image_bytes(self) -> bytes:
        buffer = BytesIO()
        Image.new("RGB", (240, 240), (255, 180, 0)).save(buffer, format="PNG")
        return buffer.getvalue()

    @override_settings(VISION_ENABLED=True, VISION_CONFIDENCE_THRESHOLD=0.72)
    def test_corrupt_image_returns_invalid_image_error(self):
        result = predict_products(b"bad-image")

        self.assertFalse(result["success"])
        self.assertTrue(result["uncertain"])
        self.assertEqual(result["error"], "invalid_image")

    @override_settings(VISION_ENABLED=True, VISION_CONFIDENCE_THRESHOLD=0.72)
    @patch("vision.service.get_recognition_backend")
    @patch("vision.service._predict_images")
    def test_low_confidence_returns_uncertain(self, mocked_predict, mocked_backend):
        mocked_backend.return_value = type("Backend", (), {"model_version": "unit-test"})()
        mocked_predict.return_value = [
            [SimpleNamespace(label_key="date", confidence=0.41)],
            [SimpleNamespace(label_key="halva", confidence=0.32)],
            [SimpleNamespace(label_key="juice", confidence=0.22)],
            [SimpleNamespace(label_key="orange", confidence=0.18)],
            [SimpleNamespace(label_key="banana", confidence=0.15)],
        ]

        result = predict_products(self._make_image_bytes())

        self.assertTrue(result["success"])
        self.assertTrue(result["uncertain"])
        self.assertEqual(result["error"], "low_confidence")
        self.assertEqual(result["detections"], [])

    @override_settings(VISION_ENABLED=True, VISION_CONFIDENCE_THRESHOLD=0.72, VISION_TOP_K=3)
    @patch("vision.service.get_recognition_backend")
    @patch("vision.service._predict_images")
    def test_multi_tile_predictions_return_multiple_detections(self, mocked_predict, mocked_backend):
        mocked_backend.return_value = type("Backend", (), {"model_version": "unit-test"})()
        mocked_predict.return_value = [
            [SimpleNamespace(label_key="date", confidence=0.91)],
            [SimpleNamespace(label_key="halva", confidence=0.83)],
            [SimpleNamespace(label_key="date", confidence=0.79)],
            [SimpleNamespace(label_key="banana", confidence=0.21)],
            [SimpleNamespace(label_key="juice", confidence=0.18)],
        ]

        result = predict_products(self._make_image_bytes())

        self.assertTrue(result["success"])
        self.assertFalse(result["uncertain"])
        self.assertEqual(result["top_label"], "خرما")
        self.assertEqual([item["label"] for item in result["detections"]], ["خرما", "حلوا"])
        self.assertEqual(result["detections"][1]["bbox"]["width"], 0.5)

    def test_persian_label_mapping_uses_exact_output_labels(self):
        detection = normalize_prediction("juice", 0.88, bbox={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}, source="full")

        self.assertEqual(detection["label"], "آبمیوه")
        self.assertEqual(detection["label_key"], "juice")

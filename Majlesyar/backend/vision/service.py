from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Iterable

from django.conf import settings

from .constants import PERSIAN_LABELS
from .preprocessing import InvalidImageError, build_tiles, preprocess_image
from .schemas import AnalysisResult, DetectionResult

logger = logging.getLogger(__name__)


def normalize_prediction(label_key: str, confidence: float, *, bbox: dict[str, float], source: str) -> DetectionResult:
    return {
        "label_key": label_key,
        "label": PERSIAN_LABELS.get(label_key, label_key),
        "confidence": round(float(confidence), 4),
        "bbox": bbox,
        "source": source,
    }


def _device_name() -> str:
    configured = getattr(settings, "VISION_DEVICE", "cpu")
    try:
        import torch
    except ImportError:
        return "cpu"
    if configured == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if configured == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return configured


@lru_cache(maxsize=1)
def get_recognition_backend() -> Any:
    model_path = getattr(settings, "VISION_MODEL_PATH", "")
    if not model_path:
        raise FileNotFoundError("VISION_MODEL_PATH is not configured")
    from .classifier import load_classifier

    return load_classifier(model_path, device=_device_name())


def _predict_images(backend: Any, images: list) -> list:
    from .classifier import predict_images

    return predict_images(backend, images)


def _aggregate_detections(
    tile_predictions: Iterable[tuple[str, dict[str, float], list]],
    *,
    threshold: float,
    top_k: int,
) -> list[DetectionResult]:
    best_by_label: dict[str, DetectionResult] = {}

    for source, bbox, predictions in tile_predictions:
        if not predictions:
            continue
        top_prediction = predictions[0]
        if top_prediction.confidence < threshold:
            continue
        current = normalize_prediction(top_prediction.label_key, top_prediction.confidence, bbox=bbox, source=source)
        existing = best_by_label.get(top_prediction.label_key)
        if existing is None or current["confidence"] > existing["confidence"]:
            best_by_label[top_prediction.label_key] = current

    detections = sorted(best_by_label.values(), key=lambda item: item["confidence"], reverse=True)
    return detections[:top_k]


def predict_products(image_source: str | Path | bytes) -> AnalysisResult:
    if not getattr(settings, "VISION_ENABLED", True):
        return {
            "success": False,
            "detections": [],
            "top_label": None,
            "top_label_key": None,
            "uncertain": True,
            "error": "vision_disabled",
            "threshold": float(getattr(settings, "VISION_CONFIDENCE_THRESHOLD", 0.7)),
            "model_version": None,
        }

    threshold = float(getattr(settings, "VISION_CONFIDENCE_THRESHOLD", 0.7))
    top_k = max(1, int(getattr(settings, "VISION_TOP_K", 3)))

    try:
        prepared = preprocess_image(
            image_source,
            max_pixels=int(getattr(settings, "VISION_MAX_PIXELS", 16_000_000)),
            max_dimension=int(getattr(settings, "VISION_MAX_DIMENSION", 1600)),
        )
    except InvalidImageError as exc:
        return {
            "success": False,
            "detections": [],
            "top_label": None,
            "top_label_key": None,
            "uncertain": True,
            "error": str(exc),
            "threshold": threshold,
            "model_version": None,
        }

    try:
        backend = get_recognition_backend()
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("Vision model unavailable: %s", exc)
        return {
            "success": False,
            "detections": [],
            "top_label": None,
            "top_label_key": None,
            "uncertain": True,
            "error": "model_unavailable",
            "threshold": threshold,
            "model_version": None,
        }

    tiles = build_tiles(prepared.image)
    predictions = _predict_images(backend, [tile for _name, tile, _bbox in tiles])
    detections = _aggregate_detections(
        (
            (name, bbox, prediction_list)
            for (name, _tile, bbox), prediction_list in zip(tiles, predictions, strict=False)
        ),
        threshold=threshold,
        top_k=top_k,
    )

    top = detections[0] if detections else None
    return {
        "success": True,
        "detections": detections,
        "top_label": top["label"] if top else None,
        "top_label_key": top["label_key"] if top else None,
        "uncertain": not detections,
        "error": None if detections else "low_confidence",
        "threshold": threshold,
        "model_version": backend.model_version,
    }


def save_prediction_result(product, analysis: AnalysisResult) -> None:
    product.photo_analysis = analysis

    if not product.contents:
        product.contents = [item["label"] for item in analysis.get("detections", [])]

    if not product.event_types and any(label in product.contents for label in ("حلوا", "خرما")):
        product.event_types = ["halva-khorma"]


def analyze_product_image(image_source: str | Path | bytes) -> AnalysisResult:
    try:
        return predict_products(image_source)
    except Exception:
        logger.exception("Unexpected error during local vision inference")
        return {
            "success": False,
            "detections": [],
            "top_label": None,
            "top_label_key": None,
            "uncertain": True,
            "error": "inference_error",
            "threshold": float(getattr(settings, "VISION_CONFIDENCE_THRESHOLD", 0.7)),
            "model_version": None,
        }

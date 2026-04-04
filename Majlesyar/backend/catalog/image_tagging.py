from __future__ import annotations

from typing import Iterable

from vision.service import analyze_product_image


def detect_pack_items(
    image_path: str,
    labels: Iterable[str] | None = None,
    top_k: int = 4,
    threshold: float = 0.24,
) -> list[str]:
    del labels, top_k, threshold
    result = analyze_product_image(image_path)
    return [item["label"] for item in result.get("detections", [])]

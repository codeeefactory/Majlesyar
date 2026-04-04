from __future__ import annotations

from typing import TypedDict


class BoundingBox(TypedDict, total=False):
    x: float
    y: float
    width: float
    height: float


class DetectionResult(TypedDict, total=False):
    label: str
    label_key: str
    confidence: float
    bbox: BoundingBox
    source: str


class AnalysisResult(TypedDict, total=False):
    success: bool
    detections: list[DetectionResult]
    top_label: str | None
    top_label_key: str | None
    uncertain: bool
    error: str | None
    threshold: float
    model_version: str | None

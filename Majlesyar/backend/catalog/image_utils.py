from __future__ import annotations

import os
import re
from pathlib import Path

from django.core.validators import FileExtensionValidator

ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")
image_extension_validator = FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)


def register_image_plugins() -> bool:
    try:
        import pillow_avif  # noqa: F401
    except ImportError:
        return False
    return True


def image_supports_extension(file_name: str | None, extension: str) -> bool:
    normalized_extension = extension.lower().lstrip(".")
    if normalized_extension != "avif":
        return True
    return register_image_plugins()


def extract_image_basename(file_name: str | None) -> str:
    if not file_name:
        return ""
    return Path(str(file_name)).name


def derive_image_label(file_name: str | None) -> str:
    base_name = extract_image_basename(file_name)
    if not base_name:
        return ""

    stem, _ext = os.path.splitext(base_name)
    normalized = re.sub(r"[_\-]+", " ", stem).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized

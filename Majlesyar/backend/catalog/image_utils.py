from __future__ import annotations

import os
import re
import unicodedata
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from PIL import Image, ImageOps

ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "avif")
image_extension_validator = FileExtensionValidator(allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
_DJANGO_STORAGE_SUFFIX_RE = re.compile(r"_[A-Za-z0-9]{7}$")
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_FILENAME_CHARACTER_RE = re.compile(r'[<>:"/\\|?*]')
_RESERVED_PRODUCT_DIRECTORIES = {"optimized", "originals"}


@deconstructible
class ProductImageStorage(FileSystemStorage):
    def get_valid_name(self, name: str) -> str:
        return normalize_image_basename(name)

    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        if max_length is not None and len(name) > max_length:
            raise ValueError("Product image path is longer than the configured field limit.")
        if self.exists(name):
            self.delete(name)
        return name


product_image_storage = ProductImageStorage()


def register_image_plugins() -> bool:
    Image.init()
    return "AVIF" in Image.OPEN or "AVIF" in Image.SAVE


def image_supports_extension(file_name: str | None, extension: str) -> bool:
    normalized_extension = extension.lower().lstrip(".")
    if normalized_extension != "avif":
        return True
    return register_image_plugins()


def prepare_image_for_existing_path(image_file, existing_name: str):
    """Return replacement content encoded for an existing public image path."""
    existing_extension = Path(existing_name).suffix.lower()
    incoming_extension = Path(image_file.name or "").suffix.lower()
    equivalent_extensions = ({".jpg", ".jpeg"},)
    if existing_extension == incoming_extension or any(
        existing_extension in group and incoming_extension in group for group in equivalent_extensions
    ):
        image_file.seek(0)
        return image_file

    target_format = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
        ".avif": "AVIF",
    }.get(existing_extension)
    if not target_format:
        image_file.seek(0)
        return image_file

    image_file.seek(0)
    with Image.open(image_file) as source:
        converted = ImageOps.exif_transpose(source).copy()

    if target_format == "JPEG" and converted.mode not in ("RGB", "L"):
        background = Image.new("RGB", converted.size, (255, 255, 255))
        alpha = converted.getchannel("A") if "A" in converted.getbands() else None
        background.paste(converted.convert("RGBA"), mask=alpha)
        converted.close()
        converted = background

    output = BytesIO()
    converted.save(output, format=target_format, quality=92)
    converted.close()
    image_file.seek(0)
    return ContentFile(output.getvalue(), name=Path(existing_name).name)


def extract_image_basename(file_name: str | None) -> str:
    if not file_name:
        return ""
    return str(file_name).replace("\\", "/").rsplit("/", 1)[-1]


def normalize_image_basename(file_name: str | None, *, fallback: str = "product-image.jpg") -> str:
    """Keep a user-visible Unicode basename while removing unsafe path characters."""
    raw_name = unicodedata.normalize("NFC", extract_image_basename(file_name)).strip().strip(".")
    raw_name = _CONTROL_CHARACTER_RE.sub("", raw_name)
    raw_name = _UNSAFE_FILENAME_CHARACTER_RE.sub("-", raw_name)
    raw_name = raw_name.strip().strip(".")
    if raw_name:
        return raw_name

    normalized_fallback = unicodedata.normalize("NFC", extract_image_basename(fallback)).strip().strip(".")
    normalized_fallback = _CONTROL_CHARACTER_RE.sub("", normalized_fallback)
    normalized_fallback = _UNSAFE_FILENAME_CHARACTER_RE.sub("-", normalized_fallback)
    return normalized_fallback or "product-image.jpg"


def clean_uploaded_image_stem(stem: str | None) -> str:
    if not stem:
        return ""
    return _DJANGO_STORAGE_SUFFIX_RE.sub("", str(stem).strip())


def product_media_directory(instance) -> str:
    """Return a readable, collision-safe media directory for one product.

    Prefer the stable product URL slug. For new products whose Persian name cannot
    produce an ASCII URL slug yet, use the readable Unicode name instead of the
    generated ``product-{uuid}`` fallback.
    """
    url_slug = str(getattr(instance, "url_slug", "") or "").strip()
    name = str(getattr(instance, "name", "") or "").strip()
    candidates = []
    if url_slug and not (url_slug.startswith("product-") and name):
        candidates.append(url_slug)
    candidates.extend((name, getattr(instance, "image_name", "")))

    for candidate in candidates:
        if not candidate:
            continue

        slug = slugify(str(candidate).strip(), allow_unicode=True)
        if slug and not slug.isdigit():
            directory = normalize_image_basename(slug, fallback="product")
            break
    else:
        directory = "product"

    directory = normalize_image_basename(directory, fallback="product")
    if directory.lower() in _RESERVED_PRODUCT_DIRECTORIES:
        directory = f"product-{directory}"
    return directory


def build_product_image_upload_path(instance, file_name: str | None) -> str:
    base_name = normalize_image_basename(file_name)
    source_stem, _source_extension = os.path.splitext(base_name)
    fallback_stem = normalize_image_basename(
        getattr(instance, "image_name", "") or getattr(instance, "name", "") or "product-image",
        fallback="product-image",
    )
    exact_stem = source_stem.strip() or os.path.splitext(fallback_stem)[0] or "product-image"
    supplied_extension = os.path.splitext(base_name)[1].lstrip(".")
    extension = supplied_extension if supplied_extension.lower() in ALLOWED_IMAGE_EXTENSIONS else "jpg"
    return f"products/{product_media_directory(instance)}/{exact_stem}.{extension}"


def build_product_gallery_image_upload_path(instance, file_name: str | None) -> str:
    """Build a collision-safe path for an additional product image."""
    product = getattr(instance, "product", None) or instance
    base_name = normalize_image_basename(file_name)
    source_stem, _source_extension = os.path.splitext(base_name)
    exact_stem = source_stem.strip() or "product-gallery-image"
    supplied_extension = os.path.splitext(base_name)[1].lstrip(".")
    extension = supplied_extension if supplied_extension.lower() in ALLOWED_IMAGE_EXTENSIONS else "jpg"
    gallery_id = normalize_image_basename(str(getattr(instance, "id", "") or "image"), fallback="image")
    return (
        f"products/{product_media_directory(product)}/gallery/"
        f"{gallery_id}/{exact_stem}.{extension}"
    )


def derive_image_label(file_name: str | None) -> str:
    base_name = extract_image_basename(file_name)
    if not base_name:
        return ""

    stem, _ext = os.path.splitext(base_name)
    stem = clean_uploaded_image_stem(stem)
    normalized = re.sub(r"[_\-]+", " ", stem).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized

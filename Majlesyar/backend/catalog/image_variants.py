from __future__ import annotations

import hashlib
import mimetypes
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
from PIL import Image, ImageOps

if TYPE_CHECKING:
    from .models import Product


RESPONSIVE_WIDTHS = (320, 480, 640, 768, 960, 1280)
DEFAULT_FALLBACK_WIDTH = 640
OPTIMIZED_ROOT = "products/optimized"
BACKUP_ROOT = "products/originals"
VARIANT_SCHEMA_VERSION = 1

FORMAT_CONFIG = {
    "avif": {
        "pil_format": "AVIF",
        "extension": "avif",
        "mime_type": "image/avif",
        "quality": 52,
        "save_kwargs": {"speed": 6},
    },
    "webp": {
        "pil_format": "WEBP",
        "extension": "webp",
        "mime_type": "image/webp",
        "quality": 76,
        "save_kwargs": {"method": 6},
    },
    "jpeg": {
        "pil_format": "JPEG",
        "extension": "jpg",
        "mime_type": "image/jpeg",
        "quality": 82,
        "save_kwargs": {"optimize": True, "progressive": True, "subsampling": "4:2:0"},
    },
}


@dataclass(slots=True)
class GeneratedVariant:
    width: int
    height: int
    path: str
    bytes: int
    mime_type: str


def register_optimized_media_types() -> None:
    mimetypes.add_type("image/avif", ".avif", strict=True)
    mimetypes.add_type("image/webp", ".webp", strict=True)
    mimetypes.add_type("image/jpeg", ".jpg", strict=True)
    mimetypes.add_type("image/jpeg", ".jpeg", strict=True)


def _ensure_image_save_registry() -> None:
    register_optimized_media_types()
    Image.init()


def _is_format_supported(format_key: str) -> bool:
    _ensure_image_save_registry()
    config = FORMAT_CONFIG[format_key]
    return config["pil_format"] in Image.SAVE


def _safe_stem(product: "Product") -> str:
    source_name = Path(product.image.name or "").stem if product.image else ""
    fallback = product.image_name or product.name or "product-image"
    return slugify(source_name) or slugify(fallback) or f"product-{str(product.pk)[:8]}"


def _product_variant_dir(product: "Product") -> str:
    return f"{OPTIMIZED_ROOT}/{product.pk}"


def _product_backup_dir(product: "Product") -> str:
    return f"{BACKUP_ROOT}/{product.pk}"


def _remove_relative_tree(relative_dir: str) -> None:
    base_dir = Path(settings.MEDIA_ROOT).resolve()
    target_dir = (base_dir / relative_dir).resolve()
    if target_dir == base_dir or base_dir not in target_dir.parents:
        return
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)


def _resize_dimensions(width: int, height: int, target_width: int) -> tuple[int, int]:
    if width <= target_width:
        return width, height
    ratio = target_width / float(width)
    target_height = max(1, round(height * ratio))
    return target_width, target_height


def _target_widths(width: int) -> list[int]:
    supported = [candidate for candidate in RESPONSIVE_WIDTHS if candidate <= width]
    if supported:
        return supported
    return [width]


def _fallback_width(widths: list[int]) -> int:
    for width in widths:
        if width >= DEFAULT_FALLBACK_WIDTH:
            return width
    return widths[-1]


def _open_source_image(image_bytes: bytes) -> Image.Image:
    with Image.open(BytesIO(image_bytes)) as source_image:
        oriented = ImageOps.exif_transpose(source_image)
        if oriented is source_image:
            return source_image.copy()
        return oriented.copy()


def _prepare_variant_source(source_image: Image.Image, format_key: str) -> Image.Image:
    image = source_image.copy()
    if format_key == "jpeg":
        if image.mode not in ("RGB", "L"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            background.paste(image.convert("RGBA"), mask=alpha)
            image = background
        elif image.mode == "L":
            image = image.convert("RGB")
    return image


def _render_variant(
    *,
    source_image: Image.Image,
    format_key: str,
    width: int,
    height: int,
    output_path: str,
) -> GeneratedVariant:
    config = FORMAT_CONFIG[format_key]
    variant_image = _prepare_variant_source(source_image, format_key)
    if variant_image.size != (width, height):
        variant_image = variant_image.resize((width, height), Image.Resampling.LANCZOS)

    output = BytesIO()
    save_kwargs = {
        "format": config["pil_format"],
        "quality": config["quality"],
        **config["save_kwargs"],
    }
    variant_image.save(output, **save_kwargs)
    content = output.getvalue()
    default_storage.save(output_path, ContentFile(content))
    variant_image.close()
    return GeneratedVariant(
        width=width,
        height=height,
        path=output_path,
        bytes=len(content),
        mime_type=config["mime_type"],
    )


def _all_variant_paths(metadata: dict) -> list[str]:
    paths: list[str] = []
    if not isinstance(metadata, dict):
        return paths

    original = metadata.get("original") or {}
    backup_path = original.get("backup_path")
    if isinstance(backup_path, str) and backup_path:
        paths.append(backup_path)

    variants = metadata.get("variants") or {}
    if isinstance(variants, dict):
        for items in variants.values():
            if not isinstance(items, list):
                continue
            for item in items:
                path = (item or {}).get("path")
                if isinstance(path, str) and path:
                    paths.append(path)
    return paths


def product_image_variants_exist(metadata: dict) -> bool:
    if not isinstance(metadata, dict):
        return False
    for relative_path in _all_variant_paths(metadata):
        if not default_storage.exists(relative_path):
            return False
    variants = metadata.get("variants") or {}
    return any((variants or {}).get(format_key) for format_key in ("avif", "webp", "jpeg"))


def clear_product_image_variants(product: "Product", *, remove_files: bool = True) -> dict:
    previous_metadata = product.image_variants or {}
    if remove_files:
        _remove_relative_tree(_product_variant_dir(product))
    product.image_variants = {}
    return previous_metadata


def ensure_product_image_variants(
    product: "Product",
    *,
    force: bool = False,
    cleanup_stale: bool = True,
) -> dict:
    if not product.image:
        return clear_product_image_variants(product, remove_files=cleanup_stale)

    with product.image.open("rb") as image_file:
        image_bytes = image_file.read()

    if not image_bytes:
        return clear_product_image_variants(product, remove_files=cleanup_stale)

    signature = hashlib.sha256(image_bytes).hexdigest()[:12]
    existing_metadata = product.image_variants or {}
    if (
        not force
        and existing_metadata.get("signature") == signature
        and product_image_variants_exist(existing_metadata)
    ):
        return existing_metadata

    source_image = _open_source_image(image_bytes)
    source_width, source_height = source_image.size
    widths = _target_widths(source_width)
    fallback_width = _fallback_width(widths)

    safe_stem = _safe_stem(product)
    original_suffix = Path(product.image.name).suffix.lower() or ".jpg"
    backup_dir = _product_backup_dir(product)
    backup_path = f"{backup_dir}/{safe_stem}-{signature}{original_suffix}"
    variant_dir = _product_variant_dir(product)

    if cleanup_stale:
        _remove_relative_tree(variant_dir)

    if not default_storage.exists(backup_path):
        default_storage.save(backup_path, ContentFile(image_bytes))

    generated_variants: dict[str, list[dict]] = {"avif": [], "webp": [], "jpeg": []}

    for format_key in ("avif", "webp", "jpeg"):
        if not _is_format_supported(format_key):
            continue

        for target_width in widths:
            output_width, output_height = _resize_dimensions(source_width, source_height, target_width)
            output_path = (
                f"{variant_dir}/"
                f"{safe_stem}-{signature}-{output_width}.{FORMAT_CONFIG[format_key]['extension']}"
            )
            generated = _render_variant(
                source_image=source_image,
                format_key=format_key,
                width=output_width,
                height=output_height,
                output_path=output_path,
            )
            generated_variants[format_key].append(
                {
                    "path": generated.path,
                    "width": generated.width,
                    "height": generated.height,
                    "bytes": generated.bytes,
                    "mime_type": generated.mime_type,
                }
            )

    source_image.close()

    metadata = {
        "schema_version": VARIANT_SCHEMA_VERSION,
        "signature": signature,
        "original": {
            "path": product.image.name,
            "backup_path": backup_path,
            "width": source_width,
            "height": source_height,
            "bytes": len(image_bytes),
            "mime_type": mimetypes.guess_type(product.image.name)[0] or "application/octet-stream",
        },
        "fallback": {
            "width": fallback_width,
            "height": _resize_dimensions(source_width, source_height, fallback_width)[1],
            "format": "jpeg",
            "sizes": {
                "card": "50vw",
                "detail": "(max-width: 640px) 100vw, 50vw",
            },
        },
        "variants": generated_variants,
    }
    return metadata


def build_product_image_payload(product: "Product", request=None) -> dict:
    metadata = product.image_variants or {}
    if not isinstance(metadata, dict):
        return {}

    original = metadata.get("original") or {}
    variants = metadata.get("variants") or {}
    fallback = metadata.get("fallback") or {}
    if not original.get("width") or not original.get("height"):
        return {}

    def build_url(relative_path: str | None) -> str | None:
        if not relative_path:
            return None
        url = default_storage.url(relative_path)
        if request:
            return request.build_absolute_uri(url)
        return url

    built_formats: dict[str, list[dict]] = {}
    for format_key in ("avif", "webp", "jpeg"):
        items = []
        for item in variants.get(format_key, []):
            relative_path = (item or {}).get("path")
            absolute_url = build_url(relative_path)
            if not absolute_url:
                continue
            items.append(
                {
                    "url": absolute_url,
                    "width": int((item or {}).get("width") or 0),
                    "height": int((item or {}).get("height") or 0),
                    "bytes": int((item or {}).get("bytes") or 0),
                    "mime_type": (item or {}).get("mime_type") or FORMAT_CONFIG[format_key]["mime_type"],
                }
            )
        built_formats[format_key] = items

    fallback_format = str(fallback.get("format") or "jpeg").lower()
    fallback_candidates = built_formats.get(fallback_format, [])
    fallback_width = int(fallback.get("width") or 0)
    fallback_item = next(
        (item for item in fallback_candidates if item["width"] == fallback_width),
        None,
    )
    if fallback_item is None and fallback_candidates:
        fallback_item = fallback_candidates[-1]

    return {
        "width": int(original["width"]),
        "height": int(original["height"]),
        "backup_url": build_url(original.get("backup_path")),
        "formats": built_formats,
        "fallback": {
            "src": fallback_item["url"] if fallback_item else None,
            "width": fallback_item["width"] if fallback_item else None,
            "height": fallback_item["height"] if fallback_item else None,
            "format": fallback_format,
            "sizes": fallback.get("sizes") or {},
        },
    }

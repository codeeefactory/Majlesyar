"""Remove product images after a committed product deletion."""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.files.storage import default_storage

from .image_utils import product_media_directory
from .image_variants import BACKUP_ROOT, OPTIMIZED_ROOT, _all_variant_paths, _remove_relative_tree

logger = logging.getLogger(__name__)


def _safe_product_path(value: str) -> str | None:
    if not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or len(path.parts) < 2 or path.parts[0] != "products":
        return None
    return path.as_posix()


def _product_paths(product) -> set[str]:
    raw_paths = [product.image.name if product.image else "", *_all_variant_paths(product.image_variants or {})]
    return {path for value in raw_paths if (path := _safe_product_path(value))}


def _media_directory(path: str) -> str | None:
    parts = PurePosixPath(path).parts
    if len(parts) < 3:
        return None
    directory = parts[2] if parts[1] in {"optimized", "originals"} and len(parts) >= 4 else parts[1]
    return directory if directory not in {"optimized", "originals", ".", ".."} else None


def cleanup_product_gallery_image(image_name: str) -> None:
    """Delete one unreferenced gallery image and purge its public cache entry."""
    safe_path = _safe_product_path(image_name)
    if not safe_path:
        return

    from .models import Product, ProductGalleryImage

    if Product.objects.filter(image=safe_path).exists() or ProductGalleryImage.objects.filter(image=safe_path).exists():
        return

    if not default_storage.exists(safe_path):
        return

    default_storage.delete(safe_path)
    from .cloudflare import purge_cloudflare_files

    result = purge_cloudflare_files({safe_path})
    if result.attempted and not result.purged:
        logger.warning("Product gallery image cache purge failed: %s", result.error)


def cleanup_deleted_product_images(product, *, using: str) -> None:
    """Delete only files/directories no surviving product refers to."""
    from .models import Product

    owned_paths = _product_paths(product)
    owned_directories = {product_media_directory(product)}
    owned_directories.update(directory for path in owned_paths if (directory := _media_directory(path)))

    referenced_paths: set[str] = set()
    referenced_directories: set[str] = set()
    for survivor in Product.objects.using(using).only("image", "image_variants", "name", "url_slug", "image_name"):
        paths = _product_paths(survivor)
        referenced_paths.update(paths)
        referenced_directories.add(product_media_directory(survivor))
        referenced_directories.update(directory for path in paths if (directory := _media_directory(path)))

    deleted_paths: set[str] = set()
    for path in sorted(owned_paths - referenced_paths):
        if default_storage.exists(path):
            default_storage.delete(path)
            deleted_paths.add(path)

    for directory in sorted(owned_directories - referenced_directories):
        if directory in {"optimized", "originals", ".", ".."} or "/" in directory or "\\" in directory:
            continue
        for relative_dir in (f"products/{directory}", f"{OPTIMIZED_ROOT}/{directory}", f"{BACKUP_ROOT}/{directory}"):
            media_root = Path(settings.MEDIA_ROOT).resolve()
            target = (media_root / relative_dir).resolve()
            tree_paths = set()
            if media_root in target.parents and target.is_dir():
                tree_paths = {
                    file.relative_to(media_root).as_posix()
                    for file in target.rglob("*")
                    if file.is_file() and media_root in file.resolve().parents
                }
            _remove_relative_tree(relative_dir)
            deleted_paths.update(path for path in tree_paths if not default_storage.exists(path))

    if deleted_paths:
        from .cloudflare import purge_cloudflare_files

        result = purge_cloudflare_files(deleted_paths)
        if result.attempted and not result.purged:
            logger.warning("Product image cache purge failed: %s", result.error)

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.image_utils import (
    clean_uploaded_image_stem,
    extract_image_basename,
    normalize_image_basename,
    product_media_directory,
)
from catalog.image_variants import (
    VARIANT_SCHEMA_VERSION,
    ensure_product_image_variants,
    product_image_variants_exist,
)
from catalog.models import Product

_VISIBLE_STORAGE_SUFFIX_RE = re.compile(r"(?:[_\s-])[A-Za-z0-9]{7}$")


def normalized_product_image_path(product: Product) -> str:
    current_basename = extract_image_basename(product.image.name)
    stem, extension = os.path.splitext(current_basename)
    clean_stem = clean_uploaded_image_stem(stem) or "product-image"
    exact_basename = normalize_image_basename(f"{clean_stem}{extension.lower()}")
    return f"products/{product_media_directory(product)}/{exact_basename}"


def clean_legacy_label(value: str) -> str:
    return _VISIBLE_STORAGE_SUFFIX_RE.sub("", (value or "").strip()).strip()


def remove_legacy_product_media_trees(product: Product) -> None:
    """Remove stale UUID media trees after stable paths are verified."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    active_paths = [product.image.name if product.image else ""]
    variants = product.image_variants or {}
    original = variants.get("original") or {}
    active_paths.append(str(original.get("backup_path") or ""))
    for format_variants in (variants.get("variants") or {}).values():
        active_paths.extend(str(item.get("path") or "") for item in format_variants if isinstance(item, dict))

    for relative_dir in (
        f"products/{product.pk}",
        f"products/optimized/{product.pk}",
        f"products/originals/{product.pk}",
    ):
        prefix = f"{relative_dir}/"
        if any(path == relative_dir or path.startswith(prefix) for path in active_paths):
            continue
        target = (media_root / relative_dir).resolve()
        if media_root not in target.parents or not target.is_dir():
            continue
        shutil.rmtree(target)


class Command(BaseCommand):
    help = "Move product originals into readable slug folders and remove old Django filename suffixes."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes. Without this flag only a dry-run is shown.")
        parser.add_argument("--product", help="Only process one product UUID or URL slug.")

    def printable(self, value: str) -> str:
        stream = getattr(self.stdout, "_out", None)
        encoding = getattr(stream, "encoding", None) or "utf-8"
        return value.encode(encoding, errors="backslashreplace").decode(encoding)

    def handle(self, *args, **options):
        queryset = Product.objects.exclude(image="")
        selector = (options.get("product") or "").strip()
        if selector:
            queryset = queryset.filter(url_slug=selector) if not re.fullmatch(r"[0-9a-fA-F-]{36}", selector) else queryset.filter(pk=selector)
            if not queryset.exists():
                raise CommandError("Product not found.")

        apply_changes = options["apply"]
        changed = 0
        skipped = 0
        failed = 0
        for product in queryset.iterator():
            source_name = product.image.name
            target_name = normalized_product_image_path(product)
            variants_current = (
                (product.image_variants or {}).get("schema_version") == VARIANT_SCHEMA_VERSION
                and product_image_variants_exist(product.image_variants or {})
            )
            if source_name == target_name and variants_current:
                if apply_changes:
                    remove_legacy_product_media_trees(product)
                skipped += 1
                continue
            action = f"{source_name} -> {target_name}" if source_name != target_name else f"refresh variants: {source_name}"
            self.stdout.write(self.printable(action))
            if not apply_changes:
                changed += 1
                continue

            storage = product.image.storage
            if not storage.exists(source_name):
                failed += 1
                self.stderr.write(self.style.ERROR(f"Missing source: {source_name}"))
                continue

            with storage.open(source_name, "rb") as source_file:
                image_bytes = source_file.read()
            saved_name = ""
            try:
                saved_name = source_name
                if source_name != target_name:
                    saved_name = storage.save(target_name, ContentFile(image_bytes))
                image_name = clean_legacy_label(product.image_name)
                image_alt = clean_legacy_label(product.image_alt)
                with transaction.atomic():
                    Product.objects.filter(pk=product.pk).update(
                        image=saved_name,
                        image_name=image_name,
                        image_alt=image_alt,
                        image_variants={},
                    )
                product.refresh_from_db()
                metadata = ensure_product_image_variants(product, force=True)
                Product.objects.filter(pk=product.pk).update(image_variants=metadata)
                product.image_variants = metadata
                remove_legacy_product_media_trees(product)
                if source_name != saved_name and storage.exists(source_name):
                    storage.delete(source_name)
                changed += 1
            except Exception as exc:
                Product.objects.filter(pk=product.pk).update(image=source_name)
                if saved_name and saved_name != source_name and storage.exists(saved_name):
                    storage.delete(saved_name)
                failed += 1
                self.stderr.write(self.style.ERROR(f"{source_name}: {exc}"))

        mode = "applied" if apply_changes else "dry-run"
        self.stdout.write(
            self.style.SUCCESS(
                f"Product image normalization {mode}: changed={changed}, skipped={skipped}, failed={failed}"
            )
        )
        if failed:
            raise CommandError(f"{failed} product image(s) failed.")

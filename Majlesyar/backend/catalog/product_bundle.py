from __future__ import annotations

import hashlib
import json
import mimetypes
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile, ZipInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import ValidationError
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError

from .image_utils import (
    ALLOWED_IMAGE_EXTENSIONS,
    image_supports_extension,
    normalize_image_basename,
)
from .models import Category, Product, Tag

BUNDLE_EXTENSION = ".mjlsyar"
BUNDLE_CONTENT_TYPE = "application/vnd.majlesyar.product+zip"
BUNDLE_FORMAT = "majlesyar-product"
BUNDLE_VERSION = 1
MANIFEST_NAME = "manifest.json"
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ARCHIVE_ENTRIES = 2
MAX_COMPRESSION_RATIO = 150

PRODUCT_FIELDS = (
    "name",
    "url_slug",
    "description",
    "price",
    "event_types",
    "contents",
    "image_name",
    "image_alt",
    "featured",
    "available",
    "is_temporary",
    "show_in_builder",
    "builder_group",
    "builder_required",
    "builder_display_order",
)


class ProductBundleError(ValueError):
    pass


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _read_product_image(product: Product) -> tuple[str, bytes] | None:
    if not product.image:
        return None
    filename = normalize_image_basename(product.image.name)
    with product.image.open("rb") as image_file:
        image_bytes = image_file.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ProductBundleError("حجم تصویر محصول برای پشتیبان‌گیری بیش از حد مجاز است.")
    return filename, image_bytes


def export_product_bundle(product: Product) -> bytes:
    product_data = {field: getattr(product, field) for field in PRODUCT_FIELDS}
    manifest = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "product": product_data,
        "categories": list(product.categories.values("name", "slug", "icon", "color")),
        "tags": list(product.tags.values("name", "slug")),
        "image": None,
    }

    image_payload = _read_product_image(product)
    archive = BytesIO()
    with ZipFile(archive, mode="w", compression=ZIP_DEFLATED, compresslevel=6) as bundle:
        if image_payload:
            filename, image_bytes = image_payload
            image_path = f"image/{filename}"
            manifest["image"] = {
                "filename": filename,
                "path": image_path,
                "size": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
            }
            bundle.writestr(image_path, image_bytes)
        bundle.writestr(MANIFEST_NAME, _json_bytes(manifest))
    return archive.getvalue()


def product_bundle_filename(product: Product) -> str:
    stem = normalize_image_basename(product.name or product.url_slug, fallback="product")
    return f"{stem}{BUNDLE_EXTENSION}"


def _validate_zip_entry(info: ZipInfo) -> None:
    path = PurePosixPath(info.filename)
    if info.flag_bits & 0x1:
        raise ProductBundleError("فایل پشتیبان رمزگذاری‌شده پشتیبانی نمی‌شود.")
    if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
        raise ProductBundleError("مسیر داخلی فایل پشتیبان نامعتبر است.")
    if ((info.external_attr >> 16) & 0o170000) == 0o120000:
        raise ProductBundleError("پیوند نمادین در فایل پشتیبان مجاز نیست.")
    if info.compress_size == 0 and info.file_size > 0:
        raise ProductBundleError("نسبت فشرده‌سازی فایل پشتیبان نامعتبر است.")
    if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
        raise ProductBundleError("فایل پشتیبان بیش از حد فشرده است.")


def _read_manifest(bundle: ZipFile, entries: dict[str, ZipInfo]) -> dict:
    info = entries.get(MANIFEST_NAME)
    if not info or info.file_size > MAX_MANIFEST_BYTES:
        raise ProductBundleError("فایل manifest.json معتبر نیست.")
    try:
        payload = json.loads(bundle.read(info).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        raise ProductBundleError("محتوای manifest.json قابل خواندن نیست.") from exc
    if not isinstance(payload, dict):
        raise ProductBundleError("ساختار فایل پشتیبان نامعتبر است.")
    if payload.get("format") != BUNDLE_FORMAT or payload.get("version") != BUNDLE_VERSION:
        raise ProductBundleError("نسخه فایل پشتیبان پشتیبانی نمی‌شود.")
    return payload


def _clean_string(value, field_name: str, max_length: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ProductBundleError(f"فیلد {field_name} باید متن باشد.")
    value = value.strip()
    if required and not value:
        raise ProductBundleError(f"فیلد {field_name} الزامی است.")
    if len(value) > max_length:
        raise ProductBundleError(f"فیلد {field_name} بیش از حد طولانی است.")
    return value


def _unique_product_slug(value: str, name: str) -> str:
    base = slugify(value or name) or "imported-product"
    candidate = base
    suffix = 2
    while Product.objects.filter(url_slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _validate_product_payload(payload) -> dict:
    if not isinstance(payload, dict):
        raise ProductBundleError("اطلاعات محصول در فایل پشتیبان نامعتبر است.")
    unknown_fields = set(payload) - set(PRODUCT_FIELDS)
    missing_fields = set(PRODUCT_FIELDS) - set(payload)
    if unknown_fields or missing_fields:
        raise ProductBundleError("فیلدهای محصول در فایل پشتیبان ناقص یا ناشناخته است.")

    name = _clean_string(payload.get("name"), "نام محصول", 255, required=True)
    price = payload.get("price")
    if price is not None and (isinstance(price, bool) or not isinstance(price, int) or price < 0):
        raise ProductBundleError("قیمت محصول نامعتبر است.")

    event_types = payload.get("event_types", [])
    contents = payload.get("contents", [])
    if not isinstance(event_types, list) or any(not isinstance(item, str) or len(item) > 64 for item in event_types):
        raise ProductBundleError("نوع مراسم محصول نامعتبر است.")
    if not isinstance(contents, list) or len(_json_bytes({"contents": contents})) > MAX_MANIFEST_BYTES:
        raise ProductBundleError("اقلام محصول نامعتبر یا بیش از حد بزرگ است.")

    cleaned = {
        "name": name,
        "url_slug": _unique_product_slug(str(payload.get("url_slug") or ""), name),
        "description": _clean_string(payload.get("description", ""), "توضیحات", 100_000),
        "price": price,
        "event_types": [item.strip() for item in event_types if item.strip()],
        "contents": contents,
        "image_name": _clean_string(payload.get("image_name", ""), "نام تصویر", 255),
        "image_alt": _clean_string(payload.get("image_alt", ""), "متن جایگزین تصویر", 255),
        "builder_group": _clean_string(payload.get("builder_group", ""), "گروه سازنده پک", 20),
        "builder_display_order": payload.get("builder_display_order", 100),
    }
    for field in ("featured", "available", "is_temporary", "show_in_builder", "builder_required"):
        value = payload.get(field, False)
        if not isinstance(value, bool):
            raise ProductBundleError(f"فیلد {field} باید بله یا خیر باشد.")
        cleaned[field] = value
    if not isinstance(cleaned["builder_display_order"], int) or cleaned["builder_display_order"] < 1:
        raise ProductBundleError("ترتیب نمایش در سازنده پک نامعتبر است.")
    return cleaned


def _validate_relation_items(payload, *, relation: str) -> list[dict]:
    if not isinstance(payload, list) or len(payload) > 100:
        raise ProductBundleError(f"فهرست {relation} نامعتبر است.")
    cleaned = []
    for item in payload:
        if not isinstance(item, dict):
            raise ProductBundleError(f"یکی از موارد {relation} نامعتبر است.")
        name = _clean_string(item.get("name"), f"نام {relation}", 128, required=True)
        slug = slugify(_clean_string(item.get("slug"), f"اسلاگ {relation}", 128, required=True))
        if not slug:
            raise ProductBundleError(f"اسلاگ {relation} نامعتبر است.")
        cleaned_item = {"name": name, "slug": slug}
        if relation == "دسته‌بندی":
            cleaned_item["icon"] = _clean_string(item.get("icon", ""), "آیکون دسته‌بندی", 32)
            cleaned_item["color"] = _clean_string(item.get("color", ""), "رنگ دسته‌بندی", 64)
        cleaned.append(cleaned_item)
    return cleaned


def _read_image(bundle: ZipFile, entries: dict[str, ZipInfo], payload) -> SimpleUploadedFile | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ProductBundleError("اطلاعات تصویر فایل پشتیبان نامعتبر است.")
    raw_filename = payload.get("filename")
    if not isinstance(raw_filename, str) or not raw_filename:
        raise ProductBundleError("نام تصویر فایل پشتیبان نامعتبر است.")
    filename = normalize_image_basename(raw_filename)
    image_path = payload.get("path")
    expected_path = f"image/{filename}"
    if (
        filename != raw_filename
        or image_path != expected_path
        or set(payload) != {"filename", "path", "size", "sha256"}
    ):
        raise ProductBundleError("نام یا مسیر تصویر فایل پشتیبان نامعتبر است.")
    extension = PurePosixPath(filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED_IMAGE_EXTENSIONS or not image_supports_extension(filename, extension):
        raise ProductBundleError("فرمت تصویر فایل پشتیبان پشتیبانی نمی‌شود.")
    info = entries.get(image_path)
    if not info or info.file_size > MAX_IMAGE_BYTES or info.file_size != payload.get("size"):
        raise ProductBundleError("اندازه تصویر فایل پشتیبان نامعتبر است.")
    image_bytes = bundle.read(info)
    if hashlib.sha256(image_bytes).hexdigest() != payload.get("sha256"):
        raise ProductBundleError("هش تصویر فایل پشتیبان مطابقت ندارد.")
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            detected_format = (image.format or "").lower()
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ProductBundleError("تصویر داخل فایل پشتیبان معتبر نیست.") from exc
    expected_formats = {
        "jpg": {"jpeg"},
        "jpeg": {"jpeg"},
        "png": {"png"},
        "webp": {"webp"},
        "avif": {"avif"},
    }
    if detected_format not in expected_formats[extension]:
        raise ProductBundleError("پسوند تصویر با محتوای واقعی آن مطابقت ندارد.")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return SimpleUploadedFile(filename, image_bytes, content_type=content_type)


def import_product_bundle(bundle_bytes: bytes) -> Product:
    if not bundle_bytes or len(bundle_bytes) > MAX_BUNDLE_BYTES:
        raise ProductBundleError("حجم فایل پشتیبان نامعتبر است.")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as bundle:
            infos = bundle.infolist()
            if not infos or len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ProductBundleError("تعداد فایل‌های داخل پشتیبان نامعتبر است.")
            if len({info.filename for info in infos}) != len(infos):
                raise ProductBundleError("فایل پشتیبان مسیر تکراری دارد.")
            for info in infos:
                _validate_zip_entry(info)
            entries = {info.filename: info for info in infos}
            manifest = _read_manifest(bundle, entries)
            if set(manifest) != {"format", "version", "product", "categories", "tags", "image"}:
                raise ProductBundleError("ساختار فایل پشتیبان نامعتبر است.")
            product_data = _validate_product_payload(manifest.get("product"))
            categories = _validate_relation_items(manifest.get("categories", []), relation="دسته‌بندی")
            tags = _validate_relation_items(manifest.get("tags", []), relation="تگ")
            image_file = _read_image(bundle, entries, manifest.get("image"))
            expected_entries = {MANIFEST_NAME}
            if image_file:
                expected_entries.add(f"image/{image_file.name}")
            if set(entries) != expected_entries:
                raise ProductBundleError("فایل پشتیبان شامل فایل ناشناخته است.")
    except (BadZipFile, OSError) as exc:
        raise ProductBundleError("فایل انتخاب‌شده یک پشتیبان معتبر محصول نیست.") from exc

    with transaction.atomic():
        category_objects = [
            Category.objects.get_or_create(
                slug=item["slug"],
                defaults={"name": item["name"], "icon": item["icon"], "color": item["color"]},
            )[0]
            for item in categories
        ]
        tag_objects = [
            Tag.objects.get_or_create(slug=item["slug"], defaults={"name": item["name"]})[0]
            for item in tags
        ]
        product = Product(**product_data)
        if image_file:
            product.image = image_file
        try:
            product.full_clean(exclude=("categories", "tags", "photo_analysis", "image_variants"))
            product.save()
            product.categories.set(category_objects)
            product.tags.set(tag_objects)
        except ValidationError as exc:
            raise ProductBundleError("اطلاعات محصول داخل فایل پشتیبان معتبر نیست.") from exc
    return product

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
import mimetypes
from pathlib import Path
import re
import time
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import requests
from django.conf import settings
from django.utils.text import slugify

from .image_utils import ALLOWED_IMAGE_EXTENSIONS
from .models import infer_event_types
from vision.service import analyze_product_image

AUTO_EVENT_CATEGORY_SLUGS = {"conference", "memorial", "halva-khorma", "party"}
NAME_FILE_SEPARATORS = ("=>", "|", "\t")

CATEGORY_ALIAS_OVERRIDES: dict[str, tuple[str, ...]] = {
    "economic": ("اقتصادی", "economical"),
    "luxury": ("لوکس", "ویژه", "vip"),
    "empty": ("خالی", "empty pack", "empty"),
}

TAG_ALIAS_OVERRIDES: dict[str, tuple[str, ...]] = {
    "student": ("دانشجویی", "student"),
    "ceremony": ("مراسمی", "مجلس", "ترحیم", "ceremony"),
    "vip": ("لوکس", "ویژه", "vip"),
    "popular": ("پرفروش", "popular", "best seller"),
    "ready-pack": ("آماده", "ready pack", "ready-pack"),
    "empty-pack": ("خالی", "empty pack", "empty-pack"),
    "birthday": ("تولد", "birthday"),
}


class RemoteCatalogError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class RemoteCategory:
    id: str
    name: str
    slug: str


@dataclass(slots=True, frozen=True)
class RemoteTag:
    id: str
    name: str
    slug: str


@dataclass(slots=True, frozen=True)
class RemoteProduct:
    id: str
    name: str
    url_slug: str
    uri: str = ""
    image: str | None = None
    image_name: str = ""
    image_alt: str = ""


@dataclass(slots=True, frozen=True)
class RemoteCatalogSnapshot:
    categories: dict[str, RemoteCategory]
    tags: dict[str, RemoteTag]
    products: list[RemoteProduct]

    @property
    def product_name_index(self) -> set[str]:
        return {normalize_lookup_text(product.name) for product in self.products if product.name}

    @property
    def product_slug_index(self) -> set[str]:
        return {product.url_slug for product in self.products if product.url_slug}


@dataclass(slots=True, frozen=True)
class ProductNameEntry:
    product_name: str
    image_key: str | None = None


@dataclass(slots=True, frozen=True)
class ProductImportCandidate:
    name: str
    image_path: Path
    description: str
    price: int | None
    category_slugs: list[str]
    tag_slugs: list[str]
    event_types: list[str]
    contents: list[str]
    image_name: str
    image_alt: str
    url_slug: str
    featured: bool
    available: bool


@dataclass(slots=True, frozen=True)
class ImageAnalysisResult:
    contents: list[str]
    raw: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ExistingProductImageMatch:
    product: RemoteProduct
    image_path: Path
    matched_key: str


def natural_sort_key(value: str | Path) -> list[Any]:
    text = str(value)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def normalize_lookup_text(value: str | None) -> str:
    if not value:
        return ""

    text = str(value)
    replacements = {
        "ي": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    text = text.lower()
    text = re.sub(r"[_\-.\\/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def truncate_text(value: str, *, max_length: int) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= max_length:
        return text
    shortened = text[: max_length - 3].rstrip(" ،,.;:")
    return f"{shortened}..."


def collect_image_paths(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        raise ValueError(f"Image directory does not exist: {images_dir}")
    if not images_dir.is_dir():
        raise ValueError(f"Image path is not a directory: {images_dir}")

    allowed_extensions = {f".{extension.lower()}" for extension in ALLOWED_IMAGE_EXTENSIONS}
    images = [
        path
        for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in allowed_extensions
    ]
    return sorted(images, key=lambda path: natural_sort_key(path.relative_to(images_dir).as_posix()))


def parse_name_file(name_file: Path) -> list[ProductNameEntry]:
    if not name_file.exists():
        raise ValueError(f"Name file does not exist: {name_file}")
    if not name_file.is_file():
        raise ValueError(f"Name file path is not a file: {name_file}")

    entries: list[ProductNameEntry] = []
    with name_file.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            entries.append(parse_name_line(line, line_number=line_number))

    if not entries:
        raise ValueError(f"Name file is empty: {name_file}")
    return entries


def parse_name_line(line: str, *, line_number: int = 0) -> ProductNameEntry:
    for separator in NAME_FILE_SEPARATORS:
        if separator not in line:
            continue
        image_key, product_name = line.split(separator, 1)
        product_name = product_name.strip()
        if not product_name:
            raise ValueError(f"Missing product name on line {line_number or '?'}: {line}")
        normalized_key = normalize_image_key(image_key)
        if not normalized_key:
            raise ValueError(f"Missing image key on line {line_number or '?'}: {line}")
        return ProductNameEntry(product_name=product_name, image_key=normalized_key)

    return ProductNameEntry(product_name=line.strip())


def normalize_image_key(value: str | None) -> str:
    return normalize_lookup_text(value)


def extract_remote_image_filename(image_url: str | None) -> str:
    if not image_url:
        return ""
    parsed = urlparse(str(image_url))
    return Path(unquote(parsed.path or "")).name


def build_remote_product_lookup_keys(product: RemoteProduct) -> list[str]:
    remote_image_name = extract_remote_image_filename(product.image)
    values = [
        product.name,
        product.url_slug,
        product.uri,
        Path(product.uri or "").name if product.uri else "",
        product.image_name,
        product.image_alt,
        remote_image_name,
        Path(remote_image_name).stem if remote_image_name else "",
    ]
    return unique_preserve_order(
        normalize_image_key(value)
        for value in values
        if normalize_image_key(value)
    )


def build_uploaded_image_filename(product: RemoteProduct, image_path: Path) -> str:
    remote_image_name = extract_remote_image_filename(product.image)
    preferred_stem = Path(remote_image_name).stem if remote_image_name else image_path.stem
    if not preferred_stem:
        preferred_stem = slugify(product.url_slug or product.name or product.id) or f"product-{product.id}"

    source_suffix = image_path.suffix or Path(remote_image_name).suffix or ".bin"
    return f"{preferred_stem}{source_suffix.lower()}"


def build_image_lookup_keys(image_path: Path, images_dir: Path) -> list[str]:
    relative_path = image_path.relative_to(images_dir).as_posix()
    stem = Path(relative_path).stem
    keys = [
        normalize_image_key(relative_path),
        normalize_image_key(image_path.name),
        normalize_image_key(stem),
    ]
    return [key for key in keys if key]


def match_existing_products_to_images(
    image_paths: list[Path],
    products: Iterable[RemoteProduct],
    *,
    images_dir: Path | None = None,
) -> tuple[list[ExistingProductImageMatch], list[Path]]:
    products_by_key: dict[str, list[RemoteProduct]] = {}
    for product in products:
        for key in build_remote_product_lookup_keys(product):
            bucket = products_by_key.setdefault(key, [])
            if product not in bucket:
                bucket.append(product)

    matches: list[ExistingProductImageMatch] = []
    unmatched_images: list[Path] = []
    matched_product_ids: set[str] = set()

    for image_path in image_paths:
        candidate_keys = (
            build_image_lookup_keys(image_path, images_dir)
            if images_dir is not None
            else unique_preserve_order(
                [normalize_image_key(image_path.name), normalize_image_key(image_path.stem)]
            )
        )

        matched_product: RemoteProduct | None = None
        matched_key = ""
        for key in candidate_keys:
            key_matches = list(dict.fromkeys(products_by_key.get(key, [])))
            if not key_matches:
                continue
            if len(key_matches) > 1:
                product_names = ", ".join(sorted(product.name for product in key_matches))
                raise ValueError(
                    f"Ambiguous remote product match for {image_path.name}: "
                    f"lookup key '{key}' matched {product_names}.",
                )
            matched_product = key_matches[0]
            matched_key = key
            break

        if matched_product is None:
            unmatched_images.append(image_path)
            continue

        if matched_product.id in matched_product_ids:
            raise ValueError(
                f"Multiple local images matched the same remote product: {matched_product.name}",
            )

        matched_product_ids.add(matched_product.id)
        matches.append(
            ExistingProductImageMatch(
                product=matched_product,
                image_path=image_path,
                matched_key=matched_key,
            )
        )

    return matches, unmatched_images


def match_images_to_names(
    image_paths: list[Path],
    name_entries: list[ProductNameEntry],
    *,
    images_dir: Path,
) -> list[tuple[Path, str]]:
    mapped_entries = [entry for entry in name_entries if entry.image_key]
    plain_entries = [entry for entry in name_entries if not entry.image_key]

    if mapped_entries and plain_entries:
        raise ValueError(
            "Name file cannot mix ordered names with filename mappings. Use one format consistently.",
        )

    if mapped_entries:
        by_image_key = {entry.image_key: entry.product_name for entry in mapped_entries if entry.image_key}
        matches: list[tuple[Path, str]] = []
        used_keys: set[str] = set()
        missing_images: list[str] = []

        for image_path in image_paths:
            match_name = ""
            for key in build_image_lookup_keys(image_path, images_dir):
                if key in by_image_key:
                    match_name = by_image_key[key]
                    used_keys.add(key)
                    break
            if not match_name:
                missing_images.append(image_path.relative_to(images_dir).as_posix())
                continue
            matches.append((image_path, match_name))

        unused_keys = sorted(set(by_image_key) - used_keys)
        if missing_images or unused_keys:
            parts: list[str] = []
            if missing_images:
                parts.append(f"missing name mappings for images: {', '.join(missing_images)}")
            if unused_keys:
                parts.append(f"unused mapped names: {', '.join(unused_keys)}")
            raise ValueError("; ".join(parts))

        return matches

    if len(image_paths) != len(plain_entries):
        raise ValueError(
            f"Image count ({len(image_paths)}) does not match name count ({len(plain_entries)}).",
        )

    return [(image_path, entry.product_name) for image_path, entry in zip(image_paths, plain_entries, strict=True)]


def analyze_image_contents(image_path: Path) -> ImageAnalysisResult:
    if not vision_runtime_is_ready():
        return ImageAnalysisResult(
            contents=[],
            raw={
                "success": False,
                "detections": [],
                "top_label": None,
                "top_label_key": None,
                "uncertain": True,
                "error": "vision_runtime_unavailable",
                "threshold": float(getattr(settings, "VISION_CONFIDENCE_THRESHOLD", 0.72)),
                "model_version": None,
            },
        )

    analysis = analyze_product_image(image_path)
    detections = analysis.get("detections") or []
    contents = unique_preserve_order(
        item.get("label", "")
        for item in detections
        if isinstance(item, dict) and item.get("label")
    )
    return ImageAnalysisResult(contents=contents, raw=analysis)


def vision_runtime_is_ready() -> bool:
    if not getattr(settings, "VISION_ENABLED", True):
        return False

    if find_spec("torch") is None:
        return False

    model_path = str(getattr(settings, "VISION_MODEL_PATH", "") or "").strip()
    if not model_path:
        return False

    return Path(model_path).exists()


def build_product_description(
    product_name: str,
    *,
    category_names: Iterable[str] = (),
    contents: Iterable[str] = (),
) -> str:
    unique_contents = unique_preserve_order(contents)
    unique_categories = unique_preserve_order(category_names)

    if unique_contents:
        preview = "، ".join(unique_contents[:4])
        if unique_categories:
            return truncate_text(
                f"{product_name} مناسب سفارش {unique_categories[0]} و شامل {preview} است.",
                max_length=400,
            )
        return truncate_text(
            f"{product_name} با اقلامی مانند {preview} برای ثبت سفارش در مجلس‌یار آماده شده است.",
            max_length=400,
        )

    if unique_categories:
        return truncate_text(
            f"{product_name} مناسب سفارش {unique_categories[0]} در مجلس‌یار است.",
            max_length=400,
        )

    return truncate_text(
        f"{product_name} برای ثبت سفارش در مجلس‌یار آماده شده است.",
        max_length=400,
    )


def build_image_alt_text(
    product_name: str,
    *,
    category_names: Iterable[str] = (),
    contents: Iterable[str] = (),
) -> str:
    unique_contents = unique_preserve_order(contents)
    unique_categories = unique_preserve_order(category_names)

    if unique_contents:
        preview = "، ".join(unique_contents[:3])
        return truncate_text(
            f"تصویر {product_name} شامل {preview}",
            max_length=255,
        )

    if unique_categories:
        return truncate_text(
            f"تصویر {product_name} مناسب {unique_categories[0]}",
            max_length=255,
        )

    return truncate_text(f"تصویر محصول {product_name}", max_length=255)


def infer_category_slugs(
    product_name: str,
    *,
    image_path: Path,
    available_categories: dict[str, RemoteCategory],
    contents: Iterable[str] = (),
    default_category_slugs: Iterable[str] = (),
) -> list[str]:
    inferred = [
        slug
        for slug in infer_event_types(product_name, "", list(contents))
        if slug in available_categories
    ]

    haystack_parts = [
        product_name,
        image_path.stem,
        *image_path.parts,
        *list(contents),
    ]
    haystack = normalize_lookup_text(" ".join(part for part in haystack_parts if part))

    for slug, category in available_categories.items():
        if slug in AUTO_EVENT_CATEGORY_SLUGS:
            continue
        aliases = [
            slug,
            slug.replace("-", " "),
            category.name,
            *CATEGORY_ALIAS_OVERRIDES.get(slug, ()),
        ]
        if any(alias and normalize_lookup_text(alias) in haystack for alias in aliases):
            inferred.append(slug)

    for slug in default_category_slugs:
        if slug in available_categories:
            inferred.append(slug)

    return unique_preserve_order(inferred)


def infer_tag_slugs(
    product_name: str,
    *,
    image_path: Path,
    available_tags: dict[str, RemoteTag],
    contents: Iterable[str] = (),
    category_slugs: Iterable[str] = (),
    default_tag_slugs: Iterable[str] = (),
) -> list[str]:
    inferred: list[str] = []
    haystack_parts = [
        product_name,
        image_path.stem,
        *image_path.parts,
        *list(contents),
        *list(category_slugs),
    ]
    haystack = normalize_lookup_text(" ".join(part for part in haystack_parts if part))

    if contents and "ready-pack" in available_tags:
        inferred.append("ready-pack")
    if "empty" in category_slugs and "empty-pack" in available_tags:
        inferred.append("empty-pack")
    if "luxury" in category_slugs and "vip" in available_tags:
        inferred.append("vip")

    for slug, tag in available_tags.items():
        aliases = [
            slug,
            slug.replace("-", " "),
            tag.name,
            *TAG_ALIAS_OVERRIDES.get(slug, ()),
        ]
        if any(alias and normalize_lookup_text(alias) in haystack for alias in aliases):
            inferred.append(slug)

    for slug in default_tag_slugs:
        if slug in available_tags:
            inferred.append(slug)

    return unique_preserve_order(inferred)


def build_import_candidates(
    *,
    images_dir: Path,
    name_file: Path,
    snapshot: RemoteCatalogSnapshot,
    default_category_slugs: Iterable[str] = (),
    default_tag_slugs: Iterable[str] = (),
    featured: bool = False,
    available: bool = True,
    price: int | None = None,
) -> list[ProductImportCandidate]:
    image_paths = collect_image_paths(images_dir)
    name_entries = parse_name_file(name_file)
    matched_images = match_images_to_names(image_paths, name_entries, images_dir=images_dir)

    candidates: list[ProductImportCandidate] = []
    for image_path, product_name in matched_images:
        analysis = analyze_image_contents(image_path)
        category_slugs = infer_category_slugs(
            product_name,
            image_path=image_path,
            available_categories=snapshot.categories,
            contents=analysis.contents,
            default_category_slugs=default_category_slugs,
        )
        tag_slugs = infer_tag_slugs(
            product_name,
            image_path=image_path,
            available_tags=snapshot.tags,
            contents=analysis.contents,
            category_slugs=category_slugs,
            default_tag_slugs=default_tag_slugs,
        )
        category_names = [
            snapshot.categories[slug].name
            for slug in category_slugs
            if slug in snapshot.categories
        ]
        description = build_product_description(
            product_name,
            category_names=category_names,
            contents=analysis.contents,
        )
        image_alt = build_image_alt_text(
            product_name,
            category_names=category_names,
            contents=analysis.contents,
        )
        event_types = unique_preserve_order(
            slug for slug in [*infer_event_types(product_name, description, analysis.contents), *category_slugs]
            if slug in AUTO_EVENT_CATEGORY_SLUGS
        )
        url_slug = slugify(image_path.stem) or ""

        candidates.append(
            ProductImportCandidate(
                name=product_name,
                image_path=image_path,
                description=description,
                price=price,
                category_slugs=category_slugs,
                tag_slugs=tag_slugs,
                event_types=event_types,
                contents=analysis.contents,
                image_name=truncate_text(product_name, max_length=255),
                image_alt=image_alt,
                url_slug=url_slug,
                featured=featured,
                available=available,
            )
        )

    return candidates


def summarize_candidate(candidate: ProductImportCandidate) -> str:
    relative_name = candidate.image_path.name
    categories = ", ".join(candidate.category_slugs) if candidate.category_slugs else "-"
    tags = ", ".join(candidate.tag_slugs) if candidate.tag_slugs else "-"
    contents = ", ".join(candidate.contents) if candidate.contents else "-"
    return (
        f"{candidate.name} | image={relative_name} | "
        f"categories={categories} | "
        f"tags={tags} | "
        f"contents={contents}"
    )


class RemoteCatalogClient:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 30,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.session = requests.Session()
        self.access_token = ""
        self.refresh_token = ""

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _send_request(self, method: str, path: str, **kwargs) -> requests.Response:
        last_error: requests.RequestException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    self._url(path),
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise RemoteCatalogError(f"Remote request failed for {path}: {exc}") from exc
                time.sleep(min(2 ** attempt, 5))
                continue

            if response.status_code not in {502, 503, 504} or attempt >= self.max_retries:
                return response

            time.sleep(min(2 ** attempt, 5))

        if last_error is not None:
            raise RemoteCatalogError(f"Remote request failed for {path}: {last_error}") from last_error
        raise RemoteCatalogError(f"Remote request failed for {path}.")

    def authenticate(self) -> None:
        response = self._send_request(
            "POST",
            "/api/v1/auth/token/",
            json={"username": self.username, "password": self.password},
        )

        if not response.ok:
            raise RemoteCatalogError(self._extract_error_message(response))

        payload = response.json()
        self.access_token = payload.get("access", "")
        self.refresh_token = payload.get("refresh", "")
        if not self.access_token:
            raise RemoteCatalogError("Remote auth succeeded but no access token was returned.")

    def _refresh_access_token(self) -> bool:
        if not self.refresh_token:
            return False

        try:
            response = self._send_request(
                "POST",
                "/api/v1/auth/token/refresh/",
                json={"refresh": self.refresh_token},
            )
        except RemoteCatalogError:
            return False

        if not response.ok:
            return False

        payload = response.json()
        self.access_token = payload.get("access", "")
        return bool(self.access_token)

    def _request(self, method: str, path: str, *, auth: bool = False, **kwargs) -> requests.Response:
        if auth and not self.access_token:
            self.authenticate()

        headers = dict(kwargs.pop("headers", {}))
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        response = self._send_request(
            method,
            path,
            headers=headers,
            **kwargs,
        )

        if auth and response.status_code == 401 and self._refresh_access_token():
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = self._send_request(
                method,
                path,
                headers=headers,
                **kwargs,
            )

        if not response.ok:
            raise RemoteCatalogError(self._extract_error_message(response))

        return response

    def _request_json(self, method: str, path: str, *, auth: bool = False, **kwargs) -> Any:
        response = self._request(method, path, auth=auth, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise RemoteCatalogError(f"Expected JSON from {path} but received invalid content.") from exc

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text.strip() or f"HTTP {response.status_code}"

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if detail:
                return str(detail)
        return str(payload)

    def scan_catalog(self) -> RemoteCatalogSnapshot:
        categories_payload = self._request_json("GET", "/api/v1/admin/categories/", auth=True)
        tags_payload = self._request_json("GET", "/api/v1/tags/")
        products_payload = self._request_json("GET", "/api/v1/admin/products/", auth=True)

        categories = {
            item["slug"]: RemoteCategory(
                id=str(item["id"]),
                name=str(item["name"]),
                slug=str(item["slug"]),
            )
            for item in categories_payload
            if item.get("slug")
        }
        tags = {
            item["slug"]: RemoteTag(
                id=str(item["id"]),
                name=str(item["name"]),
                slug=str(item["slug"]),
            )
            for item in tags_payload
            if item.get("slug")
        }
        products = [
            RemoteProduct(
                id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                url_slug=str(item.get("url_slug", "")),
                uri=str(item.get("uri", "")),
                image=str(item.get("image") or "") or None,
                image_name=str(item.get("image_name", "")),
                image_alt=str(item.get("image_alt", "")),
            )
            for item in products_payload
        ]
        return RemoteCatalogSnapshot(categories=categories, tags=tags, products=products)

    def create_product(self, candidate: ProductImportCandidate, snapshot: RemoteCatalogSnapshot) -> dict[str, Any]:
        form_fields: list[tuple[str, str]] = [
            ("name", candidate.name),
            ("description", candidate.description),
            ("input_mode", "photo_processing"),
            ("image_name", candidate.image_name),
            ("image_alt", candidate.image_alt),
            ("featured", str(candidate.featured).lower()),
            ("available", str(candidate.available).lower()),
        ]
        if candidate.url_slug:
            form_fields.append(("url_slug", candidate.url_slug))
        if candidate.price is not None:
            form_fields.append(("price", str(candidate.price)))
        for category_slug in candidate.category_slugs:
            category = snapshot.categories.get(category_slug)
            if category:
                form_fields.append(("category_ids", category.id))
        for tag_slug in candidate.tag_slugs:
            tag = snapshot.tags.get(tag_slug)
            if tag:
                form_fields.append(("tag_ids", tag.id))
        for event_type in candidate.event_types:
            form_fields.append(("event_types", event_type))
        for content in candidate.contents:
            form_fields.append(("contents", content))

        mime_type = mimetypes.guess_type(candidate.image_path.name)[0] or "application/octet-stream"
        with candidate.image_path.open("rb") as image_handle:
            response = self._request(
                "POST",
                "/api/v1/admin/products/",
                auth=True,
                data=form_fields,
                files={"image_file": (candidate.image_path.name, image_handle, mime_type)},
            )
        try:
            return response.json()
        except ValueError as exc:
            raise RemoteCatalogError("Remote product create endpoint returned invalid JSON.") from exc

    def update_product_image(self, product: RemoteProduct, image_path: Path) -> dict[str, Any]:
        form_fields = [
            ("image_name", product.image_name or ""),
            ("image_alt", product.image_alt or ""),
        ]
        upload_name = build_uploaded_image_filename(product, image_path)
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"

        with image_path.open("rb") as image_handle:
            response = self._request(
                "PATCH",
                f"/api/v1/admin/products/{product.id}/",
                auth=True,
                data=form_fields,
                files={"image_file": (upload_name, image_handle, mime_type)},
            )

        try:
            return response.json()
        except ValueError as exc:
            raise RemoteCatalogError("Remote product image update endpoint returned invalid JSON.") from exc

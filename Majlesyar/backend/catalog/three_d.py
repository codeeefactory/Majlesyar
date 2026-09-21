from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import BinaryIO

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone


GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A
GLB_BINARY_CHUNK = 0x004E4942


def build_asset_3d_upload_path(instance, _file_name: str | None) -> str:
    asset_kind = "products" if instance.__class__.__name__ == "Product" else "builder-items"
    return f"3d/{asset_kind}/{instance.pk}.glb"


def validate_glb_bytes(payload: bytes, *, max_bytes: int | None = None) -> dict:
    """Validate the GLB container and require actual mesh geometry."""
    limit = max_bytes or int(getattr(settings, "PRODUCT_3D_MAX_BYTES", 25 * 1024 * 1024))
    if len(payload) > limit:
        raise ValidationError(f"حجم مدل سه‌بعدی نباید بیشتر از {limit // (1024 * 1024)} مگابایت باشد.")
    if len(payload) < 20:
        raise ValidationError("فایل انتخاب‌شده GLB کامل نیست.")

    magic, version, declared_length = struct.unpack_from("<4sII", payload)
    if magic != GLB_MAGIC or version != 2 or declared_length != len(payload):
        raise ValidationError("هدر فایل GLB معتبر نیست.")

    chunks: dict[int, bytes] = {}
    offset = 12
    while offset < len(payload):
        if offset + 8 > len(payload):
            raise ValidationError("ساختار chunk فایل GLB ناقص است.")
        chunk_length, chunk_type = struct.unpack_from("<II", payload, offset)
        offset += 8
        chunk_end = offset + chunk_length
        if chunk_end > len(payload):
            raise ValidationError("ساختار chunk فایل GLB ناقص است.")
        chunks[chunk_type] = payload[offset:chunk_end]
        offset = chunk_end
    if offset != len(payload):
        raise ValidationError("طول chunkهای GLB با فایل مطابقت ندارد.")

    json_chunk = chunks.get(GLB_JSON_CHUNK)
    binary_chunk = chunks.get(GLB_BINARY_CHUNK)
    if not json_chunk or not binary_chunk:
        raise ValidationError("فایل GLB باید داده JSON و باینری داشته باشد.")
    try:
        document = json.loads(json_chunk.rstrip(b" \t\r\n\0").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("بخش JSON فایل GLB معتبر نیست.") from exc
    meshes = document.get("meshes") or []
    if not any(mesh.get("primitives") for mesh in meshes):
        raise ValidationError("فایل GLB هندسه سه‌بعدی ندارد.")
    if not document.get("accessors") or not document.get("bufferViews"):
        raise ValidationError("هندسه فایل GLB ناقص است.")
    return document


def validate_glb_file(upload) -> None:
    max_bytes = int(getattr(settings, "PRODUCT_3D_MAX_BYTES", 25 * 1024 * 1024))
    original_position = upload.tell() if hasattr(upload, "tell") else None
    try:
        if hasattr(upload, "seek"):
            upload.seek(0)
        validate_glb_bytes(upload.read(max_bytes + 1), max_bytes=max_bytes)
    finally:
        if original_position is not None and hasattr(upload, "seek"):
            upload.seek(original_position)


def _response_bytes(response: requests.Response, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    received = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        received += len(chunk)
        if received > max_bytes:
            raise ValidationError("خروجی سرویس سه‌بعدی از سقف حجم مجاز بزرگ‌تر است.")
        chunks.append(chunk)
    payload = b"".join(chunks)
    validate_glb_bytes(payload, max_bytes=max_bytes)
    return payload


def generate_asset_3d(
    instance,
    *,
    force: bool = False,
    session: requests.Session | None = None,
    source_sha256: str = "",
) -> dict:
    """Generate and persist one GLB through the configured private ML worker.

    Worker contract: multipart POST with ``image``, ``asset_id`` and ``model``;
    success response body must be binary GLB. The web process never imports or
    initializes the GPU model itself.
    """
    if instance.model_3d and instance.model_3d_status == "ready" and not force:
        return instance.model_3d_metadata or {}
    instance.__class__.objects.filter(pk=instance.pk).update(model_3d_status="processing", model_3d_error="")
    try:
        if not instance.image:
            raise ValidationError("این مورد تصویر ورودی ندارد.")
        endpoint = str(getattr(settings, "PRODUCT_3D_GENERATOR_URL", "") or "").strip()
        if not endpoint:
            raise ImproperlyConfigured("PRODUCT_3D_GENERATOR_URL تنظیم نشده است.")

        model_name = str(getattr(settings, "PRODUCT_3D_GENERATOR_MODEL", "triposr") or "triposr")
        timeout = int(getattr(settings, "PRODUCT_3D_GENERATOR_TIMEOUT", 180))
        max_bytes = int(getattr(settings, "PRODUCT_3D_MAX_BYTES", 25 * 1024 * 1024))
        token = str(getattr(settings, "PRODUCT_3D_GENERATOR_TOKEN", "") or "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        client = session or requests.Session()
        instance.image.open("rb")
        image_file: BinaryIO = instance.image.file
        response = client.post(
            endpoint,
            headers=headers,
            files={"image": (Path(instance.image.name).name, image_file)},
            data={"asset_id": str(instance.pk), "model": model_name, "output_format": "glb"},
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()
        payload = _response_bytes(response, max_bytes)
        digest = hashlib.sha256(payload).hexdigest()
        instance.model_3d.save(f"{instance.pk}.glb", ContentFile(payload), save=False)
        metadata = {
            "generator": model_name,
            "sha256": digest,
            "bytes": len(payload),
            "generated_at": timezone.now().isoformat(),
        }
        if source_sha256:
            metadata["source_image_sha256"] = source_sha256
        instance.__class__.objects.filter(pk=instance.pk).update(
            model_3d=instance.model_3d.name,
            model_3d_status="ready",
            model_3d_metadata=metadata,
            model_3d_error="",
        )
        instance.model_3d_status = "ready"
        instance.model_3d_metadata = metadata
        instance.model_3d_error = ""
        return metadata
    except Exception as exc:
        error_message = str(exc).strip()[:1000] or exc.__class__.__name__
        instance.__class__.objects.filter(pk=instance.pk).update(
            model_3d_status="failed",
            model_3d_error=error_message,
        )
        instance.model_3d_status = "failed"
        instance.model_3d_error = error_message
        raise
    finally:
        try:
            instance.image.close()
        except Exception:
            pass

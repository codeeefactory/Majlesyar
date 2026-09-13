from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone


GLB_MAGIC = b"glTF"


def build_asset_3d_upload_path(instance, _file_name: str | None) -> str:
    asset_kind = "products" if instance.__class__.__name__ == "Product" else "builder-items"
    return f"3d/{asset_kind}/{instance.pk}.glb"


def validate_glb_file(upload) -> None:
    max_bytes = int(getattr(settings, "PRODUCT_3D_MAX_BYTES", 25 * 1024 * 1024))
    size = getattr(upload, "size", 0) or 0
    if size > max_bytes:
        raise ValidationError(f"حجم مدل سه‌بعدی نباید بیشتر از {max_bytes // (1024 * 1024)} مگابایت باشد.")
    original_position = upload.tell() if hasattr(upload, "tell") else None
    try:
        if hasattr(upload, "seek"):
            upload.seek(0)
        if upload.read(4) != GLB_MAGIC:
            raise ValidationError("فایل انتخاب‌شده GLB معتبر نیست.")
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
    if payload[:4] != GLB_MAGIC:
        raise ValidationError("سرویس تولید سه‌بعدی فایل GLB معتبر برنگرداند.")
    return payload


def generate_asset_3d(instance, *, force: bool = False, session: requests.Session | None = None) -> dict:
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

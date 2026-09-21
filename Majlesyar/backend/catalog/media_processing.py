from __future__ import annotations

import hashlib
import io
import json
import logging
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from PIL import Image, ImageOps

from vision.constants import PERSIAN_LABELS, PERSIAN_TO_ENGLISH
from vision.service import analyze_product_image

from .models import Asset3DStatus, AssetProcessingJob, BuilderItem, Product, get_content_item_name, get_content_item_price
from .three_d import generate_asset_3d


logger = logging.getLogger(__name__)

KNOWN_PROMPTS = {
    "halva": "halva dessert",
    "date": "dates fruit",
    "orange": "orange fruit",
    "tangerine": "tangerine fruit",
    "banana": "banana fruit",
    "cake": "cake",
    "juice": "juice box or juice bottle",
    "packaging": "gift box or food package",
    "fruit": "fresh fruit",
    "drink": "beverage bottle or carton",
    "snack": "snack food",
    "addon": "small gift or decorative item",
}


def _target_type(instance: Product | BuilderItem) -> str:
    if isinstance(instance, Product):
        return AssetProcessingJob.TargetType.PRODUCT
    if isinstance(instance, BuilderItem):
        return AssetProcessingJob.TargetType.BUILDER_ITEM
    raise TypeError(f"Unsupported processing target: {instance.__class__.__name__}")


def _target_model(target_type: str):
    if target_type == AssetProcessingJob.TargetType.PRODUCT:
        return Product
    if target_type == AssetProcessingJob.TargetType.BUILDER_ITEM:
        return BuilderItem
    return None


def _sha256_field_file(field_file) -> str:
    digest = hashlib.sha256()
    field_file.open("rb")
    try:
        while chunk := field_file.read(1024 * 1024):
            digest.update(chunk)
    finally:
        field_file.close()
    return digest.hexdigest()


def _input_metadata(instance: Product | BuilderItem) -> dict[str, Any]:
    if isinstance(instance, Product):
        return {
            "name": instance.name,
            "contents": instance.contents or [],
            "show_in_builder": instance.show_in_builder,
            "builder_group": instance.builder_group,
        }
    return {
        "name": instance.name,
        "group": instance.group,
        "price": instance.price,
        "required": instance.required,
    }


def _request_sha256(source_sha256: str, metadata: dict[str, Any]) -> str:
    payload = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{source_sha256}\n{payload}".encode("utf-8")).hexdigest()


def schedule_asset_processing(instance: Product | BuilderItem, *, image_changed: bool) -> None:
    """Queue work after the surrounding DB transaction commits.

    Upload requests only persist files and a small queue row. GPU/network work is
    handled by ``process_asset_jobs`` in a separate process.
    """
    target_type = _target_type(instance)
    target_id = instance.pk
    database_alias = instance._state.db or "default"
    transaction.on_commit(
        lambda: enqueue_asset_processing(
            target_type,
            target_id,
            image_changed=image_changed,
            using=database_alias,
        ),
        using=database_alias,
        robust=True,
    )


def enqueue_asset_processing(
    target_type: str,
    target_id,
    *,
    image_changed: bool = False,
    force_requeue: bool = False,
    using: str = "default",
) -> AssetProcessingJob | None:
    model = _target_model(target_type)
    if model is None:
        raise ValueError(f"Unknown target type: {target_type}")
    instance = model.objects.using(using).filter(pk=target_id).first()
    if instance is None:
        return None

    if not instance.image:
        AssetProcessingJob.objects.using(using).filter(
            target_type=target_type,
            target_id=target_id,
            status__in=(AssetProcessingJob.Status.PENDING, AssetProcessingJob.Status.RUNNING),
        ).update(
            status=AssetProcessingJob.Status.SKIPPED,
            error="source_image_removed",
            finished_at=timezone.now(),
        )
        model.objects.using(using).filter(pk=target_id).update(
            photo_analysis={},
            model_3d_status=Asset3DStatus.MISSING,
            model_3d_error="",
        )
        return None

    try:
        source_sha256 = _sha256_field_file(instance.image)
    except Exception:
        logger.exception("Could not hash image for %s:%s", target_type, target_id)
        return None

    metadata = _input_metadata(instance)
    request_sha256 = _request_sha256(source_sha256, metadata)
    needs_3d = image_changed or not instance.model_3d or instance.model_3d_status != Asset3DStatus.READY
    actions = ["analyze"]
    if needs_3d:
        actions.append("generate_3d")

    with transaction.atomic(using=using):
        AssetProcessingJob.objects.using(using).filter(
            target_type=target_type,
            target_id=target_id,
            status=AssetProcessingJob.Status.PENDING,
        ).exclude(request_sha256=request_sha256).update(
            status=AssetProcessingJob.Status.SUPERSEDED,
            error="newer_request_queued",
            finished_at=timezone.now(),
        )
        job, created = AssetProcessingJob.objects.using(using).get_or_create(
            target_type=target_type,
            target_id=target_id,
            request_sha256=request_sha256,
            defaults={
                "source_image_name": instance.image.name,
                "source_sha256": source_sha256,
                "requested_actions": actions,
                "input_metadata": metadata,
            },
        )
        terminal_statuses = {
            AssetProcessingJob.Status.SUCCEEDED,
            AssetProcessingJob.Status.FAILED,
            AssetProcessingJob.Status.SKIPPED,
            AssetProcessingJob.Status.SUPERSEDED,
        }
        if not created and job.status in terminal_statuses and (image_changed or force_requeue):
            job.source_image_name = instance.image.name
            job.source_sha256 = source_sha256
            job.requested_actions = actions
            job.input_metadata = metadata
            job.status = AssetProcessingJob.Status.PENDING
            job.attempts = 0
            job.available_at = timezone.now()
            job.locked_at = None
            job.finished_at = None
            job.error = ""
            job.save(
                update_fields=(
                    "source_image_name",
                    "source_sha256",
                    "requested_actions",
                    "input_metadata",
                    "status",
                    "attempts",
                    "available_at",
                    "locked_at",
                    "finished_at",
                    "error",
                    "updated_at",
                ),
            )

        if "generate_3d" in actions:
            model.objects.using(using).filter(pk=target_id).update(
                model_3d_status=Asset3DStatus.QUEUED,
                model_3d_error="",
            )
    return job


def _label_key(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().lower().split())
    return PERSIAN_TO_ENGLISH.get(cleaned, cleaned.replace(" ", "-")[:80])


def _candidate_labels(instance: Product | BuilderItem) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if isinstance(instance, Product):
        declared_names = [get_content_item_name(item) for item in (instance.contents or [])]
    else:
        declared_names = [instance.name]

    for name in declared_names:
        if not name:
            continue
        key = _label_key(name)
        candidates.append({"key": key, "label": name, "prompt": KNOWN_PROMPTS.get(key, name)})

    for key, label in PERSIAN_LABELS.items():
        candidates.append({"key": key, "label": label, "prompt": KNOWN_PROMPTS[key]})

    unique: dict[str, dict[str, str]] = {}
    for candidate in candidates:
        unique.setdefault(candidate["key"], candidate)
    return list(unique.values())[:64]


def _remote_analyze(instance: Product | BuilderItem, candidates: list[dict[str, str]]) -> dict[str, Any] | None:
    endpoint = str(getattr(settings, "PRODUCT_IMAGE_ANALYZER_URL", "") or "").strip()
    if not endpoint:
        return None
    token = str(getattr(settings, "PRODUCT_3D_GENERATOR_TOKEN", "") or "").strip()
    timeout = int(getattr(settings, "PRODUCT_IMAGE_ANALYZER_TIMEOUT", 180))
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    instance.image.open("rb")
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            files={"image": (Path(instance.image.name).name, instance.image.file)},
            data={
                "asset_id": str(instance.pk),
                "labels_json": json.dumps(candidates, ensure_ascii=False),
                "top_k": str(min(12, len(candidates))),
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("detections"), list):
            raise ValueError("Analyzer returned an invalid JSON payload")
        payload["provider"] = "gpu_worker"
        return payload
    finally:
        instance.image.close()


@lru_cache(maxsize=1)
def _zero_shot_backend():
    import open_clip
    import torch

    model_name = str(getattr(settings, "VISION_ZERO_SHOT_MODEL", "ViT-B-32"))
    pretrained = str(getattr(settings, "VISION_ZERO_SHOT_PRETRAINED", "laion2b_s34b_b79k"))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    return model, preprocess, tokenizer, device, f"{model_name}:{pretrained}"


def _read_pil_image(instance: Product | BuilderItem) -> Image.Image:
    instance.image.open("rb")
    try:
        payload = instance.image.read()
    finally:
        instance.image.close()
    return ImageOps.exif_transpose(Image.open(io.BytesIO(payload))).convert("RGB")


def _zero_shot_analyze(
    instance: Product | BuilderItem,
    candidates: list[dict[str, str]],
) -> dict[str, Any]:
    import torch

    model, preprocess, tokenizer, device, model_version = _zero_shot_backend()
    image = _read_pil_image(instance)
    width, height = image.size
    tiles = [("full", image, {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0})]
    if width >= 2 and height >= 2:
        midpoint_x, midpoint_y = width // 2, height // 2
        tiles.extend(
            (
                ("top_left", image.crop((0, 0, midpoint_x, midpoint_y)), {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}),
                ("top_right", image.crop((midpoint_x, 0, width, midpoint_y)), {"x": 0.5, "y": 0.0, "width": 0.5, "height": 0.5}),
                ("bottom_left", image.crop((0, midpoint_y, midpoint_x, height)), {"x": 0.0, "y": 0.5, "width": 0.5, "height": 0.5}),
                ("bottom_right", image.crop((midpoint_x, midpoint_y, width, height)), {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5}),
            )
        )

    prompts = [f"a product photo containing {item['prompt']}" for item in candidates]
    image_batch = torch.stack([preprocess(tile[1]) for tile in tiles]).to(device)
    text_batch = tokenizer(prompts).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image_batch)
        text_features = model.encode_text(text_batch)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        probabilities = (100.0 * image_features @ text_features.T).softmax(dim=-1).cpu()

    threshold = float(getattr(settings, "VISION_ZERO_SHOT_THRESHOLD", 0.08))
    detections = []
    for label_index, spec in enumerate(candidates):
        scores = probabilities[:, label_index]
        tile_index = int(torch.argmax(scores).item())
        confidence = float(scores[tile_index].item())
        if confidence < threshold:
            continue
        source, _tile, bbox = tiles[tile_index]
        detections.append(
            {
                "label_key": spec["key"],
                "label": spec["label"],
                "confidence": round(confidence, 4),
                "bbox": bbox,
                "source": source,
            }
        )
    detections.sort(key=lambda item: item["confidence"], reverse=True)
    detections = detections[:12]
    return {
        "success": True,
        "detections": detections,
        "top_label": detections[0]["label"] if detections else None,
        "top_label_key": detections[0]["label_key"] if detections else None,
        "uncertain": not detections,
        "error": None if detections else "low_confidence",
        "threshold": threshold,
        "model_version": model_version,
        "provider": f"zero_shot_{device}",
        "image": {"width": width, "height": height},
    }


def _local_analyze(
    instance: Product | BuilderItem,
    candidates: list[dict[str, str]],
) -> dict[str, Any]:
    if hasattr(instance.image, "path"):
        result = analyze_product_image(instance.image.path)
    else:
        instance.image.open("rb")
        try:
            result = analyze_product_image(instance.image.read())
        finally:
            instance.image.close()
    result = dict(result or {})
    result["provider"] = "local_classifier"
    if (
        getattr(settings, "VISION_ZERO_SHOT_ENABLED", True)
        and result.get("error") in {"model_unavailable", "inference_error"}
    ):
        try:
            return _zero_shot_analyze(instance, candidates)
        except Exception as exc:
            logger.exception("Zero-shot image analysis failed for %s", instance.pk)
            result["zero_shot_error"] = str(exc).strip()[:500] or exc.__class__.__name__
    return result


def _pack_item_analysis(instance: Product | BuilderItem, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(instance, Product):
        declared_items = instance.contents or []
    else:
        declared_items = [{"name": instance.name, "price": instance.price}]

    detection_by_key = {
        str(item.get("label_key") or _label_key(item.get("label", ""))): item
        for item in detections
        if isinstance(item, dict)
    }
    output: list[dict[str, Any]] = []
    for position, item in enumerate(declared_items):
        name = get_content_item_name(item)
        if not name:
            continue
        match = detection_by_key.get(_label_key(name))
        output.append(
            {
                "position": position,
                "name": name,
                "price": get_content_item_price(item),
                "detected": bool(match),
                "confidence": match.get("confidence") if match else None,
                "source": "declared_pack_content" if isinstance(instance, Product) else "builder_item",
            }
        )
    return output


def analyze_asset(instance: Product | BuilderItem, source_sha256: str) -> dict[str, Any]:
    candidates = _candidate_labels(instance)
    remote_error = ""
    try:
        analysis = _remote_analyze(instance, candidates)
    except Exception as exc:
        remote_error = str(exc).strip()[:500] or exc.__class__.__name__
        logger.warning("Remote image analysis failed for %s: %s", instance.pk, remote_error)
        analysis = None
    if analysis is None:
        analysis = _local_analyze(instance, candidates)

    detections = [item for item in analysis.get("detections", []) if isinstance(item, dict)]
    analysis.update(
        {
            "source_image_sha256": source_sha256,
            "analyzed_at": timezone.now().isoformat(),
            "candidate_labels": candidates,
            "pack_items": _pack_item_analysis(instance, detections),
            "training_candidate": True,
        }
    )
    if remote_error:
        analysis["remote_error"] = remote_error
    instance.__class__.objects.filter(pk=instance.pk).update(photo_analysis=analysis)
    instance.photo_analysis = analysis
    return analysis


def _claim_next_job() -> AssetProcessingJob | None:
    now = timezone.now()
    stale_seconds = max(60, int(getattr(settings, "ASSET_PROCESSING_STALE_SECONDS", 1800)))
    AssetProcessingJob.objects.filter(
        status=AssetProcessingJob.Status.RUNNING,
        locked_at__lt=now - timedelta(seconds=stale_seconds),
    ).update(
        status=AssetProcessingJob.Status.PENDING,
        locked_at=None,
        error="stale_job_requeued",
        available_at=now,
    )

    with transaction.atomic():
        queryset = AssetProcessingJob.objects.filter(
            status=AssetProcessingJob.Status.PENDING,
            available_at__lte=now,
        ).order_by("created_at")
        if connection.features.has_select_for_update:
            queryset = queryset.select_for_update(skip_locked=connection.features.has_select_for_update_skip_locked)
        job = queryset.first()
        if job is None:
            return None
        job.status = AssetProcessingJob.Status.RUNNING
        job.attempts += 1
        job.locked_at = now
        job.error = ""
        job.save(update_fields=("status", "attempts", "locked_at", "error", "updated_at"))
        return job


def _finish_job(job: AssetProcessingJob, status: str, *, result: dict | None = None, error: str = "") -> None:
    job.status = status
    job.result = result or {}
    job.error = error[:2000]
    job.locked_at = None
    job.finished_at = timezone.now()
    job.save(update_fields=("status", "result", "error", "locked_at", "finished_at", "updated_at"))


def process_next_asset_job() -> AssetProcessingJob | None:
    job = _claim_next_job()
    if job is None:
        return None

    model = _target_model(job.target_type)
    instance = model.objects.filter(pk=job.target_id).first() if model else None
    if instance is None:
        _finish_job(job, AssetProcessingJob.Status.SKIPPED, error="target_not_found")
        return job
    if not instance.image:
        _finish_job(job, AssetProcessingJob.Status.SKIPPED, error="source_image_removed")
        return job
    if AssetProcessingJob.objects.filter(
        target_type=job.target_type,
        target_id=job.target_id,
        created_at__gt=job.created_at,
        status__in=(
            AssetProcessingJob.Status.PENDING,
            AssetProcessingJob.Status.RUNNING,
            AssetProcessingJob.Status.SUCCEEDED,
        ),
    ).exists():
        _finish_job(job, AssetProcessingJob.Status.SUPERSEDED, error="newer_request_exists")
        return job

    try:
        current_sha256 = _sha256_field_file(instance.image)
        if current_sha256 != job.source_sha256:
            _finish_job(job, AssetProcessingJob.Status.SUPERSEDED, error="source_image_changed")
            return job

        result: dict[str, Any] = {}
        if "analyze" in job.requested_actions:
            result["analysis"] = analyze_asset(instance, current_sha256)
        if "generate_3d" in job.requested_actions:
            result["model_3d"] = generate_asset_3d(
                instance,
                force=True,
                source_sha256=current_sha256,
            )
        _finish_job(job, AssetProcessingJob.Status.SUCCEEDED, result=result)
    except Exception as exc:
        error = str(exc).strip()[:2000] or exc.__class__.__name__
        max_attempts = max(1, int(getattr(settings, "ASSET_PROCESSING_MAX_ATTEMPTS", 3)))
        if job.attempts < max_attempts:
            delay = min(1800, 30 * (2 ** max(0, job.attempts - 1)))
            job.status = AssetProcessingJob.Status.PENDING
            job.available_at = timezone.now() + timedelta(seconds=delay)
            job.locked_at = None
            job.error = error
            job.save(update_fields=("status", "available_at", "locked_at", "error", "updated_at"))
        else:
            _finish_job(job, AssetProcessingJob.Status.FAILED, error=error)
        logger.exception("Asset processing failed for job %s", job.pk)
    return job

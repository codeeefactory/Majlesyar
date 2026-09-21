from __future__ import annotations

import hmac
import io
import json
import os
import threading

import numpy as np
import rembg
import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground, to_gradio_3d_orientation


app = FastAPI(title="Majlesyar image-to-3D worker", docs_url=None, redoc_url=None)
device = os.getenv("TRIPOSR_DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")
max_input_bytes = int(os.getenv("TRIPOSR_MAX_INPUT_BYTES", str(12 * 1024 * 1024)))
worker_token = os.getenv("PRODUCT_3D_GENERATOR_TOKEN", "").strip()
inference_lock = threading.Lock()
analysis_model_lock = threading.Lock()
analysis_model = None
analysis_processor = None

model = TSR.from_pretrained(
    os.getenv("TRIPOSR_MODEL", "stabilityai/TripoSR"),
    config_name="config.yaml",
    weight_name="model.ckpt",
)
model.renderer.set_chunk_size(int(os.getenv("TRIPOSR_CHUNK_SIZE", "8192")))
model.to(device)
background_session = rembg.new_session()


def _authorize(authorization: str | None) -> None:
    if not worker_token:
        return
    expected = f"Bearer {worker_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _preprocess(payload: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(payload)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image") from exc
    image = remove_background(image, background_session)
    image = resize_foreground(image, float(os.getenv("TRIPOSR_FOREGROUND_RATIO", "0.85")))
    array = np.array(image).astype(np.float32) / 255.0
    array = array[:, :, :3] * array[:, :, 3:4] + (1 - array[:, :, 3:4]) * 0.5
    return Image.fromarray((array * 255.0).astype(np.uint8))


def _open_image(payload: bytes) -> Image.Image:
    try:
        return ImageOps.exif_transpose(Image.open(io.BytesIO(payload))).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image") from exc


def _get_analysis_backend():
    global analysis_model, analysis_processor
    if analysis_model is not None and analysis_processor is not None:
        return analysis_model, analysis_processor
    with analysis_model_lock:
        if analysis_model is None or analysis_processor is None:
            from transformers import CLIPModel, CLIPProcessor

            model_name = os.getenv("IMAGE_ANALYSIS_MODEL", "openai/clip-vit-base-patch32")
            analysis_processor = CLIPProcessor.from_pretrained(model_name)
            analysis_model = CLIPModel.from_pretrained(model_name).to(device)
            analysis_model.eval()
    return analysis_model, analysis_processor


def _analysis_tiles(image: Image.Image) -> list[tuple[str, Image.Image, dict[str, float]]]:
    width, height = image.size
    midpoint_x = width // 2
    midpoint_y = height // 2
    return [
        ("full", image, {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}),
        ("top_left", image.crop((0, 0, midpoint_x, midpoint_y)), {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}),
        ("top_right", image.crop((midpoint_x, 0, width, midpoint_y)), {"x": 0.5, "y": 0.0, "width": 0.5, "height": 0.5}),
        ("bottom_left", image.crop((0, midpoint_y, midpoint_x, height)), {"x": 0.0, "y": 0.5, "width": 0.5, "height": 0.5}),
        ("bottom_right", image.crop((midpoint_x, midpoint_y, width, height)), {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5}),
    ]


def _parse_label_specs(labels_json: str) -> list[dict[str, str]]:
    try:
        raw_labels = json.loads(labels_json or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="labels_json must be valid JSON") from exc
    if not isinstance(raw_labels, list):
        raise HTTPException(status_code=400, detail="labels_json must be a list")

    labels: list[dict[str, str]] = []
    for index, value in enumerate(raw_labels[:64]):
        if isinstance(value, str):
            label = value.strip()
            spec = {"key": label.lower().replace(" ", "-"), "label": label, "prompt": label}
        elif isinstance(value, dict):
            label = str(value.get("label") or value.get("key") or "").strip()
            spec = {
                "key": str(value.get("key") or f"label-{index}").strip()[:80],
                "label": label[:120],
                "prompt": str(value.get("prompt") or label).strip()[:160],
            }
        else:
            continue
        if spec["label"] and spec["prompt"]:
            labels.append(spec)
    if len(labels) < 2:
        raise HTTPException(status_code=400, detail="At least two candidate labels are required")
    return labels


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "device": device,
        "generator": "triposr",
        "analyzer": os.getenv("IMAGE_ANALYSIS_MODEL", "openai/clip-vit-base-patch32"),
    }


@app.post("/analyze")
def analyze(
    image: UploadFile = File(...),
    asset_id: str = Form(""),
    labels_json: str = Form("[]"),
    top_k: int = Form(8),
    threshold: float = Form(0.08),
    authorization: str | None = Header(default=None),
) -> dict:
    _authorize(authorization)
    payload = image.file.read(max_input_bytes + 1)
    if not payload or len(payload) > max_input_bytes:
        raise HTTPException(status_code=413, detail="Image is empty or too large")
    source = _open_image(payload)
    labels = _parse_label_specs(labels_json)
    tiles = _analysis_tiles(source)
    model, processor = _get_analysis_backend()
    prompts = [f"a product photo containing {item['prompt']}" for item in labels]

    with inference_lock, torch.no_grad():
        inputs = processor(
            text=prompts,
            images=[tile[1] for tile in tiles],
            return_tensors="pt",
            padding=True,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        probabilities = model(**inputs).logits_per_image.softmax(dim=1).cpu()

    detections = []
    for label_index, spec in enumerate(labels):
        scores = probabilities[:, label_index]
        tile_index = int(torch.argmax(scores).item())
        confidence = float(scores[tile_index].item())
        if confidence < max(0.0, min(float(threshold), 1.0)):
            continue
        source_name, _tile, bbox = tiles[tile_index]
        detections.append(
            {
                "label_key": spec["key"],
                "label": spec["label"],
                "confidence": round(confidence, 4),
                "bbox": bbox,
                "source": source_name,
            }
        )
    detections.sort(key=lambda item: item["confidence"], reverse=True)
    detections = detections[: max(1, min(int(top_k), 20))]
    return {
        "success": True,
        "asset_id": asset_id,
        "detections": detections,
        "top_label": detections[0]["label"] if detections else None,
        "top_label_key": detections[0]["label_key"] if detections else None,
        "uncertain": not detections,
        "error": None if detections else "low_confidence",
        "threshold": threshold,
        "model_version": os.getenv("IMAGE_ANALYSIS_MODEL", "openai/clip-vit-base-patch32"),
        "image": {"width": source.width, "height": source.height},
    }


@app.post("/generate")
def generate(
    image: UploadFile = File(...),
    asset_id: str = Form(""),
    model_name: str = Form("triposr", alias="model"),
    output_format: str = Form("glb"),
    authorization: str | None = Header(default=None),
) -> Response:
    _authorize(authorization)
    if output_format.lower() != "glb":
        raise HTTPException(status_code=400, detail="Only GLB output is supported")
    payload = image.file.read(max_input_bytes + 1)
    if not payload or len(payload) > max_input_bytes:
        raise HTTPException(status_code=413, detail="Image is empty or too large")

    processed = _preprocess(payload)
    with inference_lock, torch.no_grad():
        scene_codes = model([processed], device=device)
        mesh = model.extract_mesh(
            scene_codes,
            True,
            resolution=int(os.getenv("TRIPOSR_MC_RESOLUTION", "256")),
        )[0]
        mesh = to_gradio_3d_orientation(mesh)
        glb = mesh.export(file_type="glb")
    if not isinstance(glb, bytes) or glb[:4] != b"glTF":
        raise HTTPException(status_code=500, detail="Generator returned an invalid GLB")
    return Response(
        content=glb,
        media_type="model/gltf-binary",
        headers={"X-Asset-Id": asset_id, "X-Generator": model_name},
    )

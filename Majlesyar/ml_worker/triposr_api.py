from __future__ import annotations

import hmac
import io
import os
import threading

import numpy as np
import rembg
import torch
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground, to_gradio_3d_orientation


app = FastAPI(title="Majlesyar image-to-3D worker", docs_url=None, redoc_url=None)
device = os.getenv("TRIPOSR_DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")
max_input_bytes = int(os.getenv("TRIPOSR_MAX_INPUT_BYTES", str(12 * 1024 * 1024)))
worker_token = os.getenv("PRODUCT_3D_GENERATOR_TOKEN", "").strip()
inference_lock = threading.Lock()

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


@app.get("/health")
def health() -> dict:
    return {"ok": True, "device": device, "generator": "triposr"}


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

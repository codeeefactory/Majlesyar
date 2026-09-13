from __future__ import annotations

import os
from pathlib import Path

import modal


WORKER_DIR = Path(__file__).resolve().parent

image = modal.Image.from_dockerfile(
    WORKER_DIR / "Dockerfile",
    context_dir=WORKER_DIR,
)

app = modal.App("majlesyar-product-3d")


@app.function(
    image=image,
    gpu=os.getenv("MODAL_GPU", "T4"),
    timeout=600,
    startup_timeout=1200,
    min_containers=0,
    max_containers=1,
    scaledown_window=60,
    secrets=[
        modal.Secret.from_name(
            "majlesyar-3d-worker",
            required_keys=["PRODUCT_3D_GENERATOR_TOKEN"],
        )
    ],
)
@modal.concurrent(max_inputs=1)
@modal.asgi_app()
def worker_api():
    from triposr_api import app as fastapi_app

    return fastapi_app

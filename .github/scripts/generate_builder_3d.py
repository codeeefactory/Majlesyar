#!/usr/bin/env python3
"""Generate validated GLB files for every product returned by the builder API."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


GLB_MAGIC = b"glTF"
MIN_GLB_BYTES = 1024
MAX_GLB_BYTES = 25 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--worker-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--attempts", type=int, default=2)
    return parser.parse_args()


def write_manifest(path: Path, records: list[dict[str, Any]]) -> None:
    succeeded = sum(item["status"] == "ready" for item in records)
    failed = sum(item["status"] == "failed" for item in records)
    payload = {
        "generator": "triposr",
        "total": len(records),
        "ready": succeeded,
        "failed": failed,
        "products": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_glb(payload: bytes) -> None:
    if payload[:4] != GLB_MAGIC:
        raise ValueError("worker response is not a GLB file")
    if len(payload) <= MIN_GLB_BYTES:
        raise ValueError(f"GLB is unexpectedly small ({len(payload)} bytes)")
    if len(payload) > MAX_GLB_BYTES:
        raise ValueError(f"GLB exceeds {MAX_GLB_BYTES} bytes")


def generate_one(
    session: requests.Session,
    worker_url: str,
    token: str,
    product: dict[str, Any],
    attempts: int,
) -> bytes:
    image_url = str(product.get("image") or "").strip()
    if not image_url:
        raise ValueError("product has no image URL")

    image_response = session.get(image_url, timeout=(30, 180))
    image_response.raise_for_status()
    content_type = image_response.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
    if not content_type.startswith("image/"):
        raise ValueError(f"source returned unexpected content type {content_type!r}")

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.post(
                worker_url,
                headers={"Authorization": f"Bearer {token}"},
                files={"image": ("product-image", io.BytesIO(image_response.content), content_type)},
                data={
                    "asset_id": f"product-{product['id']}",
                    "model": "triposr",
                    "output_format": "glb",
                },
                timeout=(30, 900),
            )
            response.raise_for_status()
            validate_glb(response.content)
            return response.content
        except Exception as exc:  # Continue the batch and preserve per-product errors.
            last_error = exc
            if attempt < attempts:
                print(f"  retry {attempt}/{attempts - 1}: {exc}", flush=True)
                time.sleep(5)
    assert last_error is not None
    raise last_error


def main() -> int:
    args = parse_args()
    token = os.environ.get("PRODUCT_3D_GENERATOR_TOKEN", "").strip()
    if not token:
        print("PRODUCT_3D_GENERATOR_TOKEN is required", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    model_dir = output_dir / "models" / "products"
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    session = requests.Session()
    api_response = session.get(args.api_url, timeout=(30, 180))
    api_response.raise_for_status()
    products = api_response.json()
    if not isinstance(products, list):
        raise TypeError("builder API must return a JSON list")
    products = [item for item in products if item.get("id") and item.get("image")]
    if args.limit > 0:
        products = products[: args.limit]
    if not products:
        raise RuntimeError("builder API returned no products with images")

    print(f"Generating {len(products)} builder product model(s)", flush=True)
    records: list[dict[str, Any]] = []
    for index, product in enumerate(products, start=1):
        product_id = str(product["id"])
        name = str(product.get("name") or product_id)
        print(f"[{index}/{len(products)}] {product_id} {name}", flush=True)
        record: dict[str, Any] = {
            "id": product_id,
            "name": name,
            "source_image": product["image"],
        }
        try:
            payload = generate_one(session, args.worker_url, token, product, max(args.attempts, 1))
            relative_path = Path("models") / "products" / f"{product_id}.glb"
            (output_dir / relative_path).write_bytes(payload)
            record.update(
                status="ready",
                model_path=relative_path.as_posix(),
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
            print(f"  ready: {len(payload)} bytes", flush=True)
        except Exception as exc:
            record.update(status="failed", error=str(exc)[:1000])
            print(f"  failed: {exc}", file=sys.stderr, flush=True)
        records.append(record)
        write_manifest(manifest_path, records)

    ready = sum(item["status"] == "ready" for item in records)
    failed = len(records) - ready
    print(f"Finished: {ready} ready, {failed} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

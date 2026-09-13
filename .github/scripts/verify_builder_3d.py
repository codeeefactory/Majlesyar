#!/usr/bin/env python3
"""Verify a downloaded builder 3D artifact and its manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from generate_builder_3d import validate_glb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    root = args.directory.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    records = manifest.get("products") or []
    if manifest.get("total") != len(records):
        raise ValueError("manifest total does not match product records")
    if manifest.get("ready") != len(records) or manifest.get("failed") != 0:
        raise ValueError("manifest contains failed or incomplete products")

    expected_paths: set[Path] = set()
    total_bytes = 0
    for record in records:
        relative_path = Path(record["model_path"])
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"unsafe model path: {relative_path}")
        model_path = root / relative_path
        payload = model_path.read_bytes()
        validate_glb(payload)
        if len(payload) != record["bytes"]:
            raise ValueError(f"size mismatch for {record['id']}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {record['id']}")
        expected_paths.add(model_path.resolve())
        total_bytes += len(payload)

    actual_paths = {path.resolve() for path in root.glob("models/products/*.glb")}
    if actual_paths != expected_paths:
        raise ValueError("artifact GLB files do not exactly match the manifest")

    print(json.dumps({"products": len(records), "bytes": total_bytes, "valid": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

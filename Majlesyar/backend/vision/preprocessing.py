from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedImage:
    image: Image.Image
    width: int
    height: int


def _open_image(source: str | Path | bytes | BinaryIO) -> Image.Image:
    if isinstance(source, (str, Path)):
        return Image.open(source)
    if isinstance(source, bytes):
        return Image.open(BytesIO(source))
    return Image.open(source)


def preprocess_image(
    source: str | Path | bytes | BinaryIO,
    *,
    max_pixels: int,
    max_dimension: int,
) -> PreparedImage:
    try:
        with _open_image(source) as raw_image:
            image = ImageOps.exif_transpose(raw_image)
            image.load()
            image = image.convert("RGB")
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("invalid_image") from exc

    width, height = image.size
    if width <= 0 or height <= 0:
        raise InvalidImageError("invalid_image")
    if width * height > max_pixels:
        raise InvalidImageError("image_too_large")

    if max(width, height) > max_dimension:
        image.thumbnail((max_dimension, max_dimension))

    return PreparedImage(image=image, width=image.width, height=image.height)


def build_tiles(image: Image.Image) -> list[tuple[str, Image.Image, dict[str, float]]]:
    width, height = image.size
    tiles: list[tuple[str, Image.Image, dict[str, float]]] = [
        ("full", image.copy(), {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}),
    ]

    if width < 128 or height < 128:
        return tiles

    half_w = width // 2
    half_h = height // 2
    boxes = [
        ("tile_0", (0, 0, half_w, half_h)),
        ("tile_1", (half_w, 0, width, half_h)),
        ("tile_2", (0, half_h, half_w, height)),
        ("tile_3", (half_w, half_h, width, height)),
    ]
    for name, (left, top, right, bottom) in boxes:
        tile = image.crop((left, top, right, bottom))
        bbox = {
            "x": round(left / width, 4),
            "y": round(top / height, 4),
            "width": round((right - left) / width, 4),
            "height": round((bottom - top) / height, 4),
        }
        tiles.append((name, tile, bbox))
    return tiles

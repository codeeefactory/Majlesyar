from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable

from PIL import Image


DEFAULT_LABELS = [
    "موز",
    "آبمیوه",
    "خیار",
    "سیب",
    "پرتقال",
    "حلوا",
    "خرما",
    "فینگرفود",
]

LABEL_SYNONYMS: dict[str, list[str]] = {
    "موز": ["banana"],
    "آبمیوه": ["juice", "fruit juice"],
    "خیار": ["cucumber"],
    "سیب": ["apple"],
    "پرتقال": ["orange"],
    "حلوا": ["halva", "halva dessert", "halwah"],
    "خرما": ["date", "dates", "date fruit"],
    "فینگرفود": ["finger food", "fingerfood", "canape", "snack platter"],
}


def _build_prompts(label: str) -> list[str]:
    english = LABEL_SYNONYMS.get(label, [])
    prompts = [label, f"عکس {label}", f"تصویر {label}"]
    prompts.extend(english)
    prompts.extend([f"photo of {term}" for term in english])
    return list(dict.fromkeys([p for p in prompts if p]))


def detect_pack_items(
    image_path: str,
    labels: Iterable[str] | None = None,
    top_k: int = 4,
    threshold: float = 0.24,
) -> list[str]:
    labels = list(labels or DEFAULT_LABELS)
    if not image_path or not os.path.exists(image_path):
        return []

    try:
        import torch
        import open_clip
    except Exception:
        return []

    model, preprocess, tokenizer = _get_clip()
    if model is None:
        return []

    device = _get_device()
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return []

    image_tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_tensor)
        image_features /= image_features.norm(dim=-1, keepdim=True)

        label_scores: list[tuple[str, float]] = []
        for label in labels:
            prompts = _build_prompts(label)
            if not prompts:
                continue
            text_tokens = tokenizer(prompts).to(device)
            text_features = model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            scores = (image_features @ text_features.T).squeeze(0)
            best_score = float(scores.max().item())
            label_scores.append((label, best_score))

    label_scores.sort(key=lambda item: item[1], reverse=True)
    filtered = [label for label, score in label_scores if score >= threshold]
    return filtered[:top_k]


def _get_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


@lru_cache(maxsize=1)
def _get_clip():
    try:
        import torch
        import open_clip
    except Exception:
        return None, None, None

    device = _get_device()
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="laion2b_s34b_b79k",
    )
    model.eval()
    model.to(device)
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    return model, preprocess, tokenizer

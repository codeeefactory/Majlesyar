from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import torch
from PIL import Image
from torchvision import models, transforms

from .constants import DEFAULT_MODEL_INPUT_SIZE, PRODUCT_LABELS


@dataclass(frozen=True)
class Prediction:
    label_key: str
    confidence: float


@dataclass(frozen=True)
class LoadedModel:
    model: torch.nn.Module
    class_names: tuple[str, ...]
    input_size: int
    model_version: str
    device: torch.device


def build_classifier(num_classes: int) -> torch.nn.Module:
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    return model


def load_classifier(model_path: str | Path, *, device: str) -> LoadedModel:
    resolved_path = Path(model_path)
    if not resolved_path.exists():
        raise FileNotFoundError(str(resolved_path))

    checkpoint = torch.load(resolved_path, map_location="cpu")
    class_names = tuple(checkpoint.get("class_names") or PRODUCT_LABELS)
    input_size = int(checkpoint.get("input_size") or DEFAULT_MODEL_INPUT_SIZE)
    model_version = str(checkpoint.get("model_version") or resolved_path.stem)

    model = build_classifier(len(class_names))
    state_dict = checkpoint.get("state_dict")
    if not isinstance(state_dict, dict):
        raise ValueError("model_state_missing")
    model.load_state_dict(state_dict)

    torch_device = torch.device(device)
    model.to(torch_device)
    model.eval()

    return LoadedModel(
        model=model,
        class_names=class_names,
        input_size=input_size,
        model_version=model_version,
        device=torch_device,
    )


def build_transform(input_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )


def predict_images(
    loaded_model: LoadedModel,
    images: Iterable[Image.Image],
) -> list[list[Prediction]]:
    image_list = list(images)
    if not image_list:
        return []

    transform = build_transform(loaded_model.input_size)
    batch = torch.stack([transform(image) for image in image_list]).to(loaded_model.device)

    with torch.no_grad():
        logits = loaded_model.model(batch)
        probabilities = torch.softmax(logits, dim=1).cpu()

    outputs: list[list[Prediction]] = []
    for probs in probabilities:
        ranked = torch.argsort(probs, descending=True)
        outputs.append(
            [
                Prediction(
                    label_key=loaded_model.class_names[index],
                    confidence=round(float(probs[index].item()), 4),
                )
                for index in ranked.tolist()
            ]
        )
    return outputs

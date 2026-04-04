from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from .classifier import build_classifier


@dataclass(frozen=True)
class TrainingArtifacts:
    train_dir: Path
    val_dir: Path
    output_path: Path


def build_dataloaders(data_root: Path, *, image_size: int, batch_size: int) -> tuple[DataLoader, DataLoader, list[str]]:
    train_transforms = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    eval_transforms = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    train_dataset = datasets.ImageFolder(data_root / "train", transform=train_transforms)
    val_dataset = datasets.ImageFolder(data_root / "val", transform=eval_transforms)
    class_names = train_dataset.classes

    return (
        DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0),
        DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0),
        class_names,
    )


def train_classifier(
    data_root: Path,
    output_path: Path,
    *,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    image_size: int,
    device: str,
) -> dict[str, float | str | list[str]]:
    train_loader, val_loader, class_names = build_dataloaders(data_root, image_size=image_size, batch_size=batch_size)
    model = build_classifier(len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    best_accuracy = 0.0
    best_state: dict | None = None

    for _epoch in range(epochs):
        model.train()
        for inputs, targets in train_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                logits = model(inputs)
                predicted = torch.argmax(logits, dim=1)
                correct += int((predicted == targets).sum().item())
                total += int(targets.numel())

        accuracy = correct / total if total else 0.0
        if accuracy >= best_accuracy:
            best_accuracy = accuracy
            best_state = {key: value.cpu() for key, value in model.state_dict().items()}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": best_state or model.state_dict(),
            "class_names": class_names,
            "input_size": image_size,
            "model_version": output_path.stem,
            "metrics": {"val_accuracy": round(best_accuracy, 4)},
        },
        output_path,
    )

    return {
        "output_path": str(output_path),
        "val_accuracy": round(best_accuracy, 4),
        "class_names": class_names,
    }

from __future__ import annotations

from pathlib import Path

import torch
from django.core.management.base import BaseCommand, CommandError

from vision.training import train_classifier


class Command(BaseCommand):
    help = "Train a local product classifier for halva/date/orange/tangerine/banana/cake/juice."

    def add_arguments(self, parser):
        parser.add_argument("--data-root", default="data/products")
        parser.add_argument("--output", default="models/product_classifier.pt")
        parser.add_argument("--epochs", type=int, default=8)
        parser.add_argument("--batch-size", type=int, default=16)
        parser.add_argument("--learning-rate", type=float, default=1e-3)
        parser.add_argument("--image-size", type=int, default=224)
        parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")

    def handle(self, *args, **options):
        data_root = Path(options["data_root"]).resolve()
        if not (data_root / "train").exists() or not (data_root / "val").exists():
            raise CommandError("Dataset must contain train/ and val/ directories.")

        results = train_classifier(
            data_root,
            Path(options["output"]).resolve(),
            epochs=options["epochs"],
            batch_size=options["batch_size"],
            learning_rate=options["learning_rate"],
            image_size=options["image_size"],
            device=options["device"],
        )
        self.stdout.write(self.style.SUCCESS(f"Saved model to {results['output_path']}"))
        self.stdout.write(f"Validation accuracy: {results['val_accuracy']}")

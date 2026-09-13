from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from catalog.models import Product
from catalog.three_d import validate_glb_bytes


class Command(BaseCommand):
    help = "Import generated builder product GLBs from a verified GitHub Actions artifact."

    def add_arguments(self, parser):
        parser.add_argument("artifact_dir", type=Path)
        parser.add_argument("--replace", action="store_true", help="Replace products that already have a ready model.")

    def handle(self, *args, **options):
        artifact_dir = options["artifact_dir"].resolve()
        manifest_path = artifact_dir / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Cannot read artifact manifest: {exc}") from exc

        records = manifest.get("products") or []
        if manifest.get("total") != len(records) or manifest.get("failed") != 0:
            raise CommandError("Artifact manifest is incomplete or contains failed products.")

        imported = 0
        skipped = 0
        failures: list[str] = []
        for record in records:
            product_id = str(record.get("id") or "")
            try:
                product = Product.objects.get(pk=product_id)
                if product.model_3d and product.model_3d_status == "ready" and not options["replace"]:
                    skipped += 1
                    continue

                relative_path = Path(record["model_path"])
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise ValueError("unsafe model path")
                model_path = (artifact_dir / relative_path).resolve()
                if artifact_dir not in model_path.parents:
                    raise ValueError("model path escapes artifact directory")
                payload = model_path.read_bytes()
                if len(payload) != int(record["bytes"]):
                    raise ValueError("file size does not match manifest")
                digest = hashlib.sha256(payload).hexdigest()
                if digest != record["sha256"]:
                    raise ValueError("SHA-256 does not match manifest")
                validate_glb_bytes(payload)

                product.model_3d.save(f"{product.pk}.glb", ContentFile(payload), save=False)
                metadata = {
                    "generator": manifest.get("generator", "triposr"),
                    "sha256": digest,
                    "bytes": len(payload),
                    "generated_at": timezone.now().isoformat(),
                    "source": "verified-batch-artifact",
                }
                Product.objects.filter(pk=product.pk).update(
                    model_3d=product.model_3d.name,
                    model_3d_status="ready",
                    model_3d_metadata=metadata,
                    model_3d_error="",
                )
                imported += 1
                self.stdout.write(self.style.SUCCESS(f"ready: {product.pk} {product.name}"))
            except Exception as exc:
                failures.append(f"{product_id}: {exc}")
                self.stderr.write(self.style.ERROR(f"failed: {product_id}: {exc}"))

        self.stdout.write(f"3D import finished: {imported} imported, {skipped} skipped, {len(failures)} failed")
        if failures:
            raise CommandError("One or more product models could not be imported.")

from __future__ import annotations

from pathlib import Path
import sys

from django.core.management.base import BaseCommand, CommandError

from catalog.remote_importer import (
    RemoteCatalogClient,
    RemoteCatalogError,
    build_import_candidates,
    normalize_lookup_text,
    summarize_candidate,
    vision_runtime_is_ready,
)


class Command(BaseCommand):
    help = (
        "Scan a live Majlesyar backend and bulk import products from a local image folder "
        "plus a UTF-8 names text file."
    )

    def _write(self, message: str, *, style=None) -> None:
        rendered = style(message) if style else message
        buffer = getattr(sys.stdout, "buffer", None)
        if buffer is not None:
            buffer.write(f"{rendered}\n".encode("utf-8", errors="replace"))
            buffer.flush()
            return

        try:
            self.stdout.write(rendered)
        except UnicodeEncodeError:
            fallback = rendered.encode("ascii", errors="backslashreplace").decode("ascii")
            self.stdout.write(fallback)

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default="https://majlesyar.com",
            help="Remote site base URL. Default: https://majlesyar.com",
        )
        parser.add_argument(
            "--username",
            required=True,
            help="Staff username for the remote site.",
        )
        parser.add_argument(
            "--password",
            required=True,
            help="Staff password for the remote site.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Request timeout in seconds for remote API calls. Default: 30",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=2,
            help="Retry count for transient remote network failures. Default: 2",
        )
        parser.add_argument(
            "--images-dir",
            type=Path,
            required=True,
            help="Local directory containing product images.",
        )
        parser.add_argument(
            "--names-file",
            type=Path,
            required=True,
            help=(
                "UTF-8 text file for product names. Supported formats: one name per line, "
                "or image-file|product-name mapping."
            ),
        )
        parser.add_argument(
            "--default-category-slug",
            action="append",
            default=[],
            help="Fallback category slug to apply to every imported product. Repeatable.",
        )
        parser.add_argument(
            "--default-tag-slug",
            action="append",
            default=[],
            help="Fallback tag slug to apply to every imported product. Repeatable.",
        )
        parser.add_argument(
            "--price",
            type=int,
            default=None,
            help="Optional fixed price for all imported products.",
        )
        parser.add_argument(
            "--featured",
            action="store_true",
            help="Mark all imported products as featured.",
        )
        parser.add_argument(
            "--unavailable",
            action="store_true",
            help="Mark imported products as unavailable.",
        )
        parser.add_argument(
            "--allow-duplicates",
            action="store_true",
            help="Do not skip products when a remote product with the same name or slug already exists.",
        )
        parser.add_argument(
            "--scan-only",
            action="store_true",
            help="Only scan the remote backend and print discovered categories, tags, and product count.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build import candidates and print them without uploading anything.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional limit for number of candidates to process after matching names to images.",
        )

    def handle(self, *args, **options):
        client = RemoteCatalogClient(
            base_url=options["base_url"],
            username=options["username"],
            password=options["password"],
            timeout=options["timeout"],
            max_retries=options["retries"],
        )

        try:
            snapshot = client.scan_catalog()
        except RemoteCatalogError as exc:
            raise CommandError(str(exc)) from exc

        self._write("Remote backend scan completed.", style=self.style.SUCCESS)
        self._write(f"Base URL: {options['base_url'].rstrip('/')}")
        self._write(f"Categories ({len(snapshot.categories)}): {', '.join(sorted(snapshot.categories))}")
        self._write(f"Tags ({len(snapshot.tags)}): {', '.join(sorted(snapshot.tags))}")
        self._write(f"Existing products: {len(snapshot.products)}")
        if not vision_runtime_is_ready():
            self._write(
                "Local vision runtime is not available on this machine. "
                "Detected contents will stay empty locally unless torch/model files are installed, "
                "but uploaded products still use input_mode=photo_processing.",
                style=self.style.WARNING,
            )

        if options["scan_only"]:
            return

        default_category_slugs = [slug.strip() for slug in options["default_category_slug"] if slug.strip()]
        default_tag_slugs = [slug.strip() for slug in options["default_tag_slug"] if slug.strip()]

        unknown_category_slugs = [slug for slug in default_category_slugs if slug not in snapshot.categories]
        if unknown_category_slugs:
            raise CommandError(
                f"Unknown default category slug(s): {', '.join(unknown_category_slugs)}",
            )

        unknown_tag_slugs = [slug for slug in default_tag_slugs if slug not in snapshot.tags]
        if unknown_tag_slugs:
            raise CommandError(
                f"Unknown default tag slug(s): {', '.join(unknown_tag_slugs)}",
            )

        try:
            candidates = build_import_candidates(
                images_dir=options["images_dir"],
                name_file=options["names_file"],
                snapshot=snapshot,
                default_category_slugs=default_category_slugs,
                default_tag_slugs=default_tag_slugs,
                featured=bool(options["featured"]),
                available=not bool(options["unavailable"]),
                price=options["price"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["limit"] is not None:
            candidates = candidates[: max(0, options["limit"])]

        if not candidates:
            self._write("No import candidates were found.")
            return

        self._write(f"Prepared {len(candidates)} import candidate(s).")

        created_count = 0
        skipped_count = 0
        failed_count = 0
        existing_name_index = set(snapshot.product_name_index)
        existing_slug_index = set(snapshot.product_slug_index)

        for index, candidate in enumerate(candidates, start=1):
            is_duplicate = False
            reason = ""
            if not options["allow_duplicates"]:
                normalized_name = normalize_lookup_text(candidate.name)
                if normalized_name and normalized_name in existing_name_index:
                    is_duplicate = True
                    reason = "same remote product name already exists"
                if not is_duplicate and candidate.url_slug and candidate.url_slug in existing_slug_index:
                    is_duplicate = True
                    reason = "same remote product slug already exists"

            prefix = f"[{index}/{len(candidates)}] {candidate.name}"

            if is_duplicate:
                skipped_count += 1
                self._write(f"{prefix} -> skipped ({reason})", style=self.style.WARNING)
                continue

            self._write(f"{prefix} -> {summarize_candidate(candidate)}")

            if options["dry_run"]:
                existing_name_index.add(normalize_lookup_text(candidate.name))
                if candidate.url_slug:
                    existing_slug_index.add(candidate.url_slug)
                continue

            try:
                created = client.create_product(candidate, snapshot)
            except RemoteCatalogError as exc:
                failed_count += 1
                self._write(f"{prefix} -> failed ({exc})", style=self.style.ERROR)
                continue

            created_count += 1
            existing_name_index.add(normalize_lookup_text(candidate.name))
            if candidate.url_slug:
                existing_slug_index.add(candidate.url_slug)
            self._write(
                f"{prefix} -> created with id {created.get('id', 'unknown')}",
                style=self.style.SUCCESS,
            )

        if options["dry_run"]:
            self._write("Dry run finished. No products were uploaded.", style=self.style.SUCCESS)
            return

        self._write(
            f"Import finished. Created={created_count}, Skipped={skipped_count}, Failed={failed_count}",
            style=self.style.SUCCESS,
        )

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from catalog.remote_importer import (
    RemoteCatalogClient,
    RemoteCatalogError,
    collect_image_paths,
    match_existing_products_to_images,
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_cache_busted_url(url: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}sync_verify={int(time.time() * 1000)}"


def verify_remote_image(local_image_path: Path, remote_image_url: str, *, timeout: int) -> dict[str, Any]:
    local_bytes = local_image_path.read_bytes()
    response = requests.get(build_cache_busted_url(remote_image_url), timeout=timeout)
    response.raise_for_status()
    remote_bytes = response.content

    local_hash = sha256_bytes(local_bytes)
    remote_hash = sha256_bytes(remote_bytes)
    if local_hash != remote_hash:
        raise CommandError(
            f"Uploaded image verification failed for {local_image_path.name}: "
            f"local sha256={local_hash}, remote sha256={remote_hash}",
        )

    return {
        "remote_image_url": remote_image_url,
        "local_sha256": local_hash,
        "remote_sha256": remote_hash,
    }


def find_matching_remote_image(local_image_path: Path, remote_image_url: str, *, timeout: int) -> dict[str, Any] | None:
    try:
        local_bytes = local_image_path.read_bytes()
        response = requests.get(build_cache_busted_url(remote_image_url), timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None

    local_hash = sha256_bytes(local_bytes)
    remote_hash = sha256_bytes(response.content)
    if local_hash != remote_hash:
        return None

    return {
        "remote_image_url": remote_image_url,
        "local_sha256": local_hash,
        "remote_sha256": remote_hash,
    }


def capture_product_screenshots(
    *,
    base_url: str,
    screenshot_dir: Path,
    updated_products: list[dict[str, str]],
    timeout_seconds: int,
) -> dict[str, str]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CommandError(
            "Playwright is not installed in this environment. "
            "Install it with `py -m pip install playwright` and `py -m playwright install chromium`.",
        ) from exc

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, str] = {}

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as exc:
            raise CommandError(
                "Chromium is not installed for Playwright. "
                "Run `py -m playwright install chromium` and try again.",
            ) from exc

        page = browser.new_page(viewport={"width": 1440, "height": 1800}, device_scale_factor=1)
        page.set_default_timeout(timeout_seconds * 1000)

        try:
            for product in updated_products:
                uri = product.get("uri", "")
                if not uri:
                    raise CommandError(f"Updated product {product.get('name', 'unknown')} did not return a public URI.")

                product_url = f"{base_url.rstrip('/')}{uri}"
                page.goto(build_cache_busted_url(product_url), wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")
                try:
                    page.locator('img[src*="/media/products/"]').first.wait_for(state="visible")
                except PlaywrightError:
                    page.wait_for_timeout(1500)
                page.wait_for_timeout(1000)

                screenshot_name = slugify(product.get("url_slug") or product.get("id") or product.get("name") or "product")
                screenshot_path = screenshot_dir / f"{screenshot_name}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshots[str(product.get("id", ""))] = str(screenshot_path)
        finally:
            browser.close()

    return screenshots


class Command(BaseCommand):
    help = (
        "Scan a live Majlesyar backend, match local images to existing products, "
        "replace only their product photos, and capture verification screenshots."
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
            "--images-dir",
            type=Path,
            required=True,
            help="Local directory containing replacement product images.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Request timeout in seconds for remote API calls and verification downloads. Default: 60",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Retry count for transient remote network failures. Default: 3",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional limit for how many matched products to update.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only scan, match, and print what would be updated.",
        )
        parser.add_argument(
            "--skip-screenshots",
            action="store_true",
            help="Skip browser screenshots after image verification.",
        )
        parser.add_argument(
            "--screenshot-dir",
            type=Path,
            default=Path("artifacts") / "remote-product-screenshots",
            help="Directory where product screenshots and the JSON report should be stored.",
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
        self._write(f"Categories: {len(snapshot.categories)}")
        self._write(f"Tags: {len(snapshot.tags)}")
        self._write(f"Products: {len(snapshot.products)}")

        image_paths = collect_image_paths(options["images_dir"])
        matches, unmatched_images = match_existing_products_to_images(
            image_paths,
            snapshot.products,
            images_dir=options["images_dir"],
        )

        if options["limit"] is not None:
            matches = matches[: max(0, options["limit"])]

        if not matches:
            raise CommandError("No existing remote products matched the provided image folder.")

        self._write(f"Matched images to existing products: {len(matches)}")
        for match in matches:
            self._write(
                f"- {match.product.name} <- {match.image_path.name} (lookup key: {match.matched_key})"
            )

        if unmatched_images:
            self._write(
                f"Unmatched images ({len(unmatched_images)}): "
                f"{', '.join(path.name for path in unmatched_images)}",
                style=self.style.WARNING,
            )

        if options["dry_run"]:
            self._write("Dry run finished. No remote products were changed.", style=self.style.SUCCESS)
            return

        screenshot_dir: Path = options["screenshot_dir"]
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        updated_products: list[dict[str, str]] = []
        report_items: list[dict[str, Any]] = []

        for index, match in enumerate(matches, start=1):
            prefix = f"[{index}/{len(matches)}] {match.product.name}"
            try:
                verification = None
                updated: dict[str, Any]

                if match.product.image:
                    verification = find_matching_remote_image(
                        match.image_path,
                        match.product.image,
                        timeout=options["timeout"],
                    )

                if verification is not None:
                    updated = {
                        "id": match.product.id,
                        "name": match.product.name,
                        "url_slug": match.product.url_slug,
                        "uri": match.product.uri,
                        "image": match.product.image,
                    }
                    action = "already matched remote image; skipped upload"
                else:
                    updated = client.update_product_image(match.product, match.image_path)
                    remote_image_url = str(updated.get("image") or "").strip()
                    if not remote_image_url:
                        raise CommandError(f"{prefix} did not return an image URL after update.")
                    verification = verify_remote_image(
                        match.image_path,
                        remote_image_url,
                        timeout=options["timeout"],
                    )
                    action = "image replaced and verified"
            except (RemoteCatalogError, requests.RequestException, CommandError) as exc:
                raise CommandError(f"{prefix} failed: {exc}") from exc

            updated_products.append(
                {
                    "id": str(updated.get("id", "")),
                    "name": str(updated.get("name", match.product.name)),
                    "url_slug": str(updated.get("url_slug", match.product.url_slug)),
                    "uri": str(updated.get("uri", match.product.uri)),
                }
            )
            report_items.append(
                {
                    "product_id": str(updated.get("id", "")),
                    "product_name": str(updated.get("name", match.product.name)),
                    "url_slug": str(updated.get("url_slug", match.product.url_slug)),
                    "uri": str(updated.get("uri", match.product.uri)),
                    "matched_local_image": str(match.image_path),
                    "matched_lookup_key": match.matched_key,
                    "action": action,
                    **verification,
                }
            )
            style = self.style.WARNING if action.startswith("already matched") else self.style.SUCCESS
            self._write(f"{prefix} -> {action}.", style=style)

        screenshot_map: dict[str, str] = {}
        if not options["skip_screenshots"]:
            screenshot_map = capture_product_screenshots(
                base_url=options["base_url"],
                screenshot_dir=screenshot_dir,
                updated_products=updated_products,
                timeout_seconds=options["timeout"],
            )
            for item in report_items:
                item["screenshot_path"] = screenshot_map.get(item["product_id"], "")

        report_payload = {
            "base_url": options["base_url"].rstrip("/"),
            "updated_count": len(report_items),
            "unmatched_images": [str(path) for path in unmatched_images],
            "screenshots_enabled": not options["skip_screenshots"],
            "items": report_items,
        }
        report_path = screenshot_dir / "replace_remote_product_images_report.json"
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self._write(f"Verification report written to {report_path}", style=self.style.SUCCESS)
        if screenshot_map:
            self._write(f"Screenshots saved to {screenshot_dir}", style=self.style.SUCCESS)

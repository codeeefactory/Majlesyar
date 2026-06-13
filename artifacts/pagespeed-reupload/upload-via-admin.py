from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(r"C:\Users\Sadjad Rgz\Documents\Majlesyar2")
REUPLOAD_ROOT = Path(
    os.environ.get(
        "MAJLESYAR_REUPLOAD_ROOT",
        str(PROJECT_ROOT / "artifacts" / "pagespeed-reupload"),
    )
)
MANIFEST_PATH = REUPLOAD_ROOT / "manifest.json"
SCREENSHOT_DIR = REUPLOAD_ROOT / "screenshots"
BASE_URL = "https://majlesyar.com"
ADMIN_BASE = f"{BASE_URL}/majmanage"
USERNAME = os.environ.get("MAJLESYAR_ADMIN_USER", "admin")
PASSWORD = os.environ.get("MAJLESYAR_ADMIN_PASSWORD", "admin")
FORCE_UPLOAD_SLUGS = {
    slug.strip()
    for slug in os.environ.get("MAJLESYAR_FORCE_UPLOAD_SLUGS", "").split(",")
    if slug.strip()
}


def read_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def fetch_product_snapshot(item: dict) -> dict:
    response = requests.get(f"{BASE_URL}/api/v1/products/", timeout=30)
    response.raise_for_status()
    products = response.json()
    current = next(
        (entry for entry in products if entry.get("id") == item["id"] or entry.get("url_slug") == item["slug"]),
        None,
    )
    if not current:
        raise RuntimeError(f"Could not find {item['slug']} in API response")
    return current


def verify_product_api(item: dict, snapshot: dict) -> dict:
    current = fetch_product_snapshot(item)

    if current.get("name") != snapshot.get("name"):
        raise RuntimeError(f"name changed for {item['slug']}: {current.get('name')}")
    if current.get("image_name") != snapshot.get("image_name"):
        raise RuntimeError(f"image_name changed for {item['slug']}: {current.get('image_name')}")
    if current.get("image_alt") != snapshot.get("image_alt"):
        raise RuntimeError(f"image_alt changed for {item['slug']}: {current.get('image_alt')}")

    image_url = str(current.get("image") or "")
    if not image_url.lower().endswith(".webp"):
        raise RuntimeError(f"image URL for {item['slug']} is not webp: {image_url}")

    image_response = requests.get(image_url, timeout=30)
    image_response.raise_for_status()
    content_type = image_response.headers.get("content-type", "")
    if "image/webp" not in content_type.lower():
        raise RuntimeError(f"unexpected content type for {item['slug']}: {content_type}")

    return {"image": image_url, "content_type": content_type}


def upload_product(page, item: dict, snapshot: dict) -> None:
    change_url = f"{ADMIN_BASE}/catalog/product/{item['id']}/change/"
    upload_path = PROJECT_ROOT / item["upload_ready"]

    page.goto(change_url, wait_until="domcontentloaded")
    page.locator("#id_name").wait_for()

    current_name = page.locator("#id_name").input_value()
    current_image_name = page.locator("#id_image_name").input_value()
    current_alt = page.locator("#id_image_alt").input_value()

    if current_name != snapshot.get("name"):
        raise RuntimeError(f"Unexpected name on admin form for {item['slug']}: {current_name}")
    if current_image_name != snapshot.get("image_name"):
        raise RuntimeError(f"Unexpected image_name on admin form for {item['slug']}: {current_image_name}")
    if current_alt != snapshot.get("image_alt"):
        raise RuntimeError(f"Unexpected image_alt on admin form for {item['slug']}: {current_alt}")

    page.locator("#id_image").set_input_files(
        [
            {
                "name": item["upload_filename"],
                "mimeType": "image/webp",
                "buffer": upload_path.read_bytes(),
            }
        ]
    )
    page.locator('[name="_save"]').click()
    page.wait_for_timeout(4000)

    if page.locator(".errornote, ul.errorlist").count():
        raise RuntimeError(f"Validation error shown after saving {item['slug']}")


def screenshot_public_product(context, item: dict) -> None:
    page = context.new_page()
    page.goto(f"{BASE_URL}/product/{item['slug']}", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(SCREENSHOT_DIR / f"{item['slug']}.png"), full_page=True)
    page.close()


def main() -> None:
    manifest = read_manifest()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        admin_context = browser.new_context()
        login_page = admin_context.new_page()
        login_page.goto(f"{ADMIN_BASE}/login/?next=/majmanage/", wait_until="domcontentloaded")
        login_page.locator('input[name="username"]').fill(USERNAME)
        login_page.locator('input[name="password"]').fill(PASSWORD)
        login_page.locator('button[type="submit"], input[type="submit"]').click()
        login_page.wait_for_url("**/majmanage/")
        login_page.close()

        for item in manifest:
            snapshot = fetch_product_snapshot(item)
            current_image = str(snapshot.get("image") or "").lower()
            should_force_upload = item["slug"] in FORCE_UPLOAD_SLUGS
            if current_image.endswith(".webp") and not should_force_upload:
                print(f"Skipping upload for {item['slug']} because it is already webp")
            elif current_image.endswith((".jpg", ".jpeg")) or should_force_upload:
                print(f"Uploading {item['slug']} using {item['upload_filename']}")
                page = admin_context.new_page()
                try:
                    upload_product(page, item, snapshot)
                finally:
                    page.close()
            else:
                raise RuntimeError(f"Unexpected source image format for {item['slug']}: {snapshot.get('image')}")

            verification = None
            last_error = None
            for _ in range(12):
                try:
                    verification = verify_product_api(item, snapshot)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(5)
            if verification is None:
                raise RuntimeError(f"Verification failed for {item['slug']}: {last_error}") from last_error
            print(f"Verified {item['slug']}: {verification['image']} ({verification['content_type']})")

        public_context = browser.new_context()
        for item in manifest:
            screenshot_public_product(public_context, item)
        public_context.close()

        admin_context.close()
        browser.close()


if __name__ == "__main__":
    main()

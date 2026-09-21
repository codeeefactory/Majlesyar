"""Cloudflare cache purge for admin actions and deleted product images."""

from dataclasses import dataclass
from urllib.parse import quote

import requests
from django.conf import settings


@dataclass(frozen=True)
class CloudflarePurgeResult:
    attempted: bool
    purged_everything: bool = False
    error: str = ""


@dataclass(frozen=True)
class CloudflareFilePurgeResult:
    attempted: bool
    purged: bool = False
    error: str = ""


def purge_cloudflare_files(paths: set[str]) -> CloudflareFilePurgeResult:
    """Invalidate only deleted media URLs; never purge the whole zone automatically."""
    if not paths:
        return CloudflareFilePurgeResult(attempted=False)

    token = str(getattr(settings, "CLOUDFLARE_API_TOKEN", "")).strip()
    zone_id = str(getattr(settings, "CLOUDFLARE_ZONE_ID", "")).strip()
    if not token or not zone_id:
        return CloudflareFilePurgeResult(attempted=False, error="Cloudflare credentials are not configured.")

    base_url = str(getattr(settings, "CLOUDFLARE_PUBLIC_BASE_URL", "https://majlesyar.com")).rstrip("/")
    media_url = str(settings.MEDIA_URL).strip("/")
    urls = [f"{base_url}/{media_url}/{quote(path, safe='/')}" for path in sorted(paths)]
    try:
        for offset in range(0, len(urls), 30):
            response = requests.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"files": urls[offset:offset + 30]},
                timeout=(3, 8),
            )
            payload = response.json() if response.content else {}
            if not response.ok or not isinstance(payload, dict) or not payload.get("success"):
                return CloudflareFilePurgeResult(attempted=True, error="Cloudflare rejected exact-file purge.")
    except (requests.RequestException, ValueError):
        return CloudflareFilePurgeResult(attempted=True, error="Cloudflare exact-file purge failed.")
    return CloudflareFilePurgeResult(attempted=True, purged=True)


def purge_cloudflare_cache() -> CloudflarePurgeResult:
    """Purge the complete zone cache after an explicit administrator request."""
    token = str(getattr(settings, "CLOUDFLARE_API_TOKEN", "")).strip()
    zone_id = str(getattr(settings, "CLOUDFLARE_ZONE_ID", "")).strip()
    if not token or not zone_id:
        return CloudflarePurgeResult(
            attempted=False,
            error="تنظیمات اتصال Cloudflare کامل نیست؛ کش پاک نشد.",
        )

    try:
        response = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"purge_everything": True},
            timeout=(3, 12),
        )
        payload = response.json() if response.content else {}
        if response.ok and isinstance(payload, dict) and payload.get("success"):
            return CloudflarePurgeResult(attempted=True, purged_everything=True)
    except (requests.RequestException, ValueError):
        pass

    return CloudflarePurgeResult(
        attempted=True,
        error="Cloudflare درخواست را نپذیرفت؛ کش پاک نشد.",
    )

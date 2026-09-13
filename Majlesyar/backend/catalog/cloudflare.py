"""Cloudflare cache purge used only by the explicit admin dashboard action."""

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass(frozen=True)
class CloudflarePurgeResult:
    attempted: bool
    purged_everything: bool = False
    error: str = ""


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

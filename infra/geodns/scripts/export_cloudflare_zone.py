#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


API_ROOT = "https://api.cloudflare.com/client/v4"


def api_get(path: str, token: str) -> dict:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export current Cloudflare DNS records before GeoDNS cutover.")
    parser.add_argument("--zone-name", default=os.environ.get("CLOUDFLARE_ZONE_NAME", "majlesyar.com"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("CLOUDFLARE_API_TOKEN is required")

    zone_query = urllib.parse.urlencode({"name": args.zone_name})
    zone_response = api_get(f"/zones?{zone_query}", token)
    zone_result = zone_response.get("result") or []
    if not zone_result:
        raise SystemExit(f"No Cloudflare zone found for {args.zone_name}")
    zone_id = zone_result[0]["id"]

    page = 1
    records: list[dict] = []
    while True:
        record_query = urllib.parse.urlencode({"per_page": 5000, "page": page})
        record_response = api_get(f"/zones/{zone_id}/dns_records?{record_query}", token)
        batch = record_response.get("result") or []
        records.extend(batch)
        info = record_response.get("result_info") or {}
        if page >= int(info.get("total_pages", 1)):
            break
        page += 1

    export = {
        "zone_name": args.zone_name,
        "zone_id": zone_id,
        "record_count": len(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(export, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

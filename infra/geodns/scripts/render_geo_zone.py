#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_site_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "site" not in data:
        raise ValueError(f"{path} does not contain a top-level 'site' object")
    return data["site"]


def load_state(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def rr_entry(rr_type: str, content: str, ttl: int | None = None) -> dict:
    rr_type = rr_type.lower()
    if ttl is None:
        return {rr_type: content}
    return {rr_type: {"content": content, "ttl": ttl}}


def ensure_record(records: dict[str, list], qname: str) -> list:
    if qname not in records:
        records[qname] = []
    return records[qname]


def add_address_records(records: dict[str, list], qname: str, entry: dict, ttl: int | None = None) -> None:
    target = ensure_record(records, qname)
    if entry.get("ipv4"):
        target.append(rr_entry("a", str(entry["ipv4"]), ttl=ttl))
    if entry.get("ipv6"):
        target.append(rr_entry("aaaa", str(entry["ipv6"]), ttl=ttl))


def pick_origin(site: dict, policy_name: str) -> dict:
    origins = site["origins"]
    if policy_name not in origins:
        raise ValueError(f"Unknown policy target '{policy_name}'")
    return origins[policy_name]


def build_zone(site: dict, state: dict) -> dict:
    domain = site["domain"]
    serial = int(state.get("serial") or datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    normal_policy = site.get("normal_policy", {"iran": "iran", "default": "global"})
    policy = state.get("policy") or normal_policy
    degraded = policy != normal_policy or state.get("mode") == "manual"
    ttl = int(site["failover_ttl"] if degraded else site["default_ttl"])

    records: dict[str, list] = {}
    apex = ensure_record(records, domain)
    soa = site["soa"]
    apex.append(
        rr_entry(
            "soa",
            f"{soa['primary']} {soa['hostmaster']} {serial} {soa['refresh']} {soa['retry']} {soa['expire']} {soa['minimum']}",
        )
    )
    for nameserver in site["nameservers"]:
        apex.append(rr_entry("ns", nameserver["name"], ttl=ttl))

    for nameserver in site["nameservers"]:
        add_address_records(records, nameserver["name"], nameserver, ttl=ttl)

    for origin in site["origins"].values():
        add_address_records(records, origin["name"], origin, ttl=ttl)

    add_address_records(records, site["policy_hosts"]["iran"], pick_origin(site, policy["iran"]), ttl=ttl)
    add_address_records(records, site["policy_hosts"]["default"], pick_origin(site, policy["default"]), ttl=ttl)

    for qname, entries in (site.get("extra_records") or {}).items():
        target = ensure_record(records, qname)
        for entry in entries:
            target.append(
                rr_entry(
                    entry["type"],
                    str(entry["content"]),
                    ttl=int(entry["ttl"]) if entry.get("ttl") is not None else None,
                )
            )

    return {
        "domains": [
            {
                "domain": domain,
                "ttl": ttl,
                "records": records,
                "services": {
                    domain: {
                        "default": [site["service_template"], site["policy_hosts"]["default"]],
                    }
                },
            }
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a PowerDNS GeoIP zone file from site config and failover state.")
    parser.add_argument("--site-config", required=True, type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    site = load_site_config(args.site_config)
    state = load_state(args.state)
    zone = build_zone(site, state)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(zone, allow_unicode=False, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()

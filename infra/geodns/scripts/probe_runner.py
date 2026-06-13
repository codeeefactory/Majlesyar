#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_site_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "site" not in data:
        raise ValueError(f"{path} does not contain a top-level 'site' object")
    return data["site"]


def run_dig(name: str, qtype: str, server: str | None = None, tcp: bool = False) -> list[str]:
    command = ["dig", "+short", "+time=2", "+tries=1"]
    if tcp:
        command.append("+tcp")
    if server:
        command.append(f"@{server}")
    command.extend([name, qtype])
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip().rstrip(".") for line in result.stdout.splitlines() if line.strip()]


def query_soa_serial(server_ip: str, domain: str, tcp: bool = False) -> int | None:
    records = run_dig(domain, "SOA", server=server_ip, tcp=tcp)
    if not records:
        return None
    fields = records[0].split()
    if len(fields) < 3:
        return None
    try:
        return int(fields[2])
    except ValueError:
        return None


def http_check(url: str, expect_json_ok: bool) -> dict:
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "majlesyar-probe/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read()
            duration_ms = round((time.monotonic() - started) * 1000, 1)
            ok = 200 <= response.status < 400
            payload_ok = True
            if expect_json_ok:
                try:
                    payload = json.loads(body.decode("utf-8"))
                    payload_ok = bool(payload.get("ok"))
                except Exception:
                    payload_ok = False
            return {
                "ok": ok and payload_ok,
                "status": response.status,
                "latency_ms": duration_ms,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": exc.__class__.__name__,
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
        }


def tls_check(hostname: str) -> dict:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, 443), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as wrapped:
                certificate = wrapped.getpeercert()
        expires_at = datetime.strptime(certificate["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_remaining = (expires_at - datetime.now(timezone.utc)).days
        return {
            "valid": days_remaining >= 0,
            "days_remaining": days_remaining,
            "not_after": expires_at.isoformat().replace("+00:00", "Z"),
        }
    except Exception as exc:
        return {
            "valid": False,
            "days_remaining": -1,
            "error": exc.__class__.__name__,
        }


def compare_sets(actual: list[str], expected: list[str]) -> bool:
    return set(actual) == set(expected) and bool(actual)


def emit_prometheus(result: dict) -> str:
    region = result["region"]
    lines = [
        "# HELP majlesyar_dns_authoritative_ok Authoritative DNS availability from this probe.",
        "# TYPE majlesyar_dns_authoritative_ok gauge",
        f'majlesyar_dns_authoritative_ok{{region="{region}"}} {1 if result["dns"]["authoritative"]["overall_ok"] else 0}',
        "# HELP majlesyar_dns_response_correct GeoDNS public answer correctness from this probe.",
        "# TYPE majlesyar_dns_response_correct gauge",
        f'majlesyar_dns_response_correct{{region="{region}"}} {1 if result["dns"]["public_answer"]["correct_overall"] else 0}',
    ]
    for server_name, serial in result["dns"]["serial"]["servers"].items():
        if serial is not None:
            lines.extend(
                [
                    "# HELP majlesyar_dns_zone_serial Observed SOA serial per authoritative server.",
                    "# TYPE majlesyar_dns_zone_serial gauge",
                    f'majlesyar_dns_zone_serial{{region="{region}",server="{server_name}"}} {serial}',
                ]
            )
    for origin_name, checks in result["origins"].items():
        for scheme in ("http", "https"):
            entry = checks[scheme]
            lines.extend(
                [
                    "# HELP majlesyar_origin_check_ok Origin health check from a probe.",
                    "# TYPE majlesyar_origin_check_ok gauge",
                    f'majlesyar_origin_check_ok{{region="{region}",origin="{origin_name}",scheme="{scheme}"}} {1 if entry["ok"] else 0}',
                ]
            )
            if entry.get("latency_ms") is not None:
                lines.extend(
                    [
                        "# HELP majlesyar_origin_latency_ms Origin health check latency in milliseconds.",
                        "# TYPE majlesyar_origin_latency_ms gauge",
                        f'majlesyar_origin_latency_ms{{region="{region}",origin="{origin_name}",scheme="{scheme}"}} {entry["latency_ms"]}',
                    ]
                )
    for host, tls in result["tls"].items():
        lines.extend(
            [
                "# HELP majlesyar_tls_valid TLS validity for monitored hostnames.",
                "# TYPE majlesyar_tls_valid gauge",
                f'majlesyar_tls_valid{{region="{region}",host="{host}"}} {1 if tls["valid"] else 0}',
                "# HELP majlesyar_tls_days_remaining Remaining TLS validity in days.",
                "# TYPE majlesyar_tls_days_remaining gauge",
                f'majlesyar_tls_days_remaining{{region="{region}",host="{host}"}} {tls["days_remaining"]}',
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GeoDNS and origin checks from an Iran or global probe host.")
    parser.add_argument("--site-config", required=True, type=Path)
    parser.add_argument("--region", choices=["iran", "global"], required=True)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--prom-out", required=True, type=Path)
    args = parser.parse_args()

    site = load_site_config(args.site_config)
    domain = site["domain"]
    expected_policy_host = site["policy_hosts"]["iran" if args.region == "iran" else "default"]

    nameserver_results = []
    serials: dict[str, int | None] = {}
    authoritative_ok = True
    for nameserver in site["nameservers"]:
        udp_serial = query_soa_serial(nameserver["ipv4"], domain, tcp=False)
        tcp_serial = query_soa_serial(nameserver["ipv4"], domain, tcp=True)
        server_ok = udp_serial is not None and tcp_serial is not None
        authoritative_ok = authoritative_ok and server_ok
        nameserver_results.append(
            {
                "server": nameserver["name"],
                "ipv4": nameserver["ipv4"],
                "udp_ok": udp_serial is not None,
                "tcp_ok": tcp_serial is not None,
            }
        )
        serials[nameserver["name"]] = udp_serial or tcp_serial

    apex_a = run_dig(domain, "A")
    apex_aaaa = run_dig(domain, "AAAA")
    expected_a = run_dig(expected_policy_host, "A")
    expected_aaaa = run_dig(expected_policy_host, "AAAA")

    origins: dict[str, dict] = {}
    for origin_name, origin in site["origins"].items():
        health_path = origin.get("health_path", "/")
        expect_json_ok = health_path.endswith("/health/")
        base_host = origin["name"]
        http = http_check(f"http://{base_host}{health_path}", expect_json_ok=expect_json_ok)
        https = http_check(f"https://{base_host}{health_path}", expect_json_ok=expect_json_ok)
        origins[origin_name] = {
            "http": http,
            "https": https,
            "overall_ok": bool(http["ok"] and https["ok"]),
        }

    tls = {
        domain: tls_check(domain),
    }
    for origin in site["origins"].values():
        tls[origin["name"]] = tls_check(origin["name"])

    result = {
        "region": args.region,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dns": {
            "authoritative": {
                "overall_ok": authoritative_ok,
                "servers": nameserver_results,
            },
            "public_answer": {
                "a": apex_a,
                "aaaa": apex_aaaa,
                "expected_a": expected_a,
                "expected_aaaa": expected_aaaa,
                "correct_a": compare_sets(apex_a, expected_a),
                "correct_aaaa": compare_sets(apex_aaaa, expected_aaaa),
                "correct_overall": compare_sets(apex_a, expected_a) and compare_sets(apex_aaaa, expected_aaaa),
            },
            "serial": {
                "consistent": len({serial for serial in serials.values() if serial is not None}) == 1,
                "servers": serials,
            },
        },
        "origins": origins,
        "tls": tls,
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    args.prom_out.parent.mkdir(parents=True, exist_ok=True)
    args.prom_out.write_text(emit_prometheus(result), encoding="utf-8")


if __name__ == "__main__":
    main()

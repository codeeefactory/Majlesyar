#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import time
import urllib.request
from pathlib import Path


def service_up(service_name: str) -> bool:
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", service_name],
        check=False,
    ).returncode == 0


def docker_container_healthy(container_name: str) -> bool | None:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip().lower()
    return value in {"healthy", "running"}


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def metric_line(name: str, value: int | float, labels: dict[str, str] | None = None) -> str:
    label_text = ""
    if labels:
        rendered = ",".join(f'{key}="{value}"' for key, value in labels.items())
        label_text = f"{{{rendered}}}"
    return f"{name}{label_text} {value}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit local host metrics for PowerDNS or web origin hosts.")
    parser.add_argument("--role", choices=["dns", "origin", "maintenance"], required=True)
    parser.add_argument("--prom-out", required=True, type=Path)
    parser.add_argument("--maxmind-path", type=Path, default=Path("/var/lib/GeoIP/GeoLite2-Country.mmdb"))
    parser.add_argument("--container-name", default="majlesyar")
    parser.add_argument("--nginx-url", default="http://127.0.0.1/api/v1/health/")
    parser.add_argument("--app-url", default="http://127.0.0.1:8000/api/v1/health/")
    args = parser.parse_args()

    lines = [
        "# HELP majlesyar_host_metric Local host metric produced by custom collectors.",
        "# TYPE majlesyar_host_metric gauge",
        metric_line("majlesyar_collector_last_run_timestamp", int(time.time())),
    ]

    if args.role == "dns":
        lines.append(metric_line("majlesyar_powerdns_service_up", 1 if service_up("pdns") else 0))
        age_seconds = -1
        if args.maxmind_path.exists():
            age_seconds = int(time.time() - args.maxmind_path.stat().st_mtime)
        lines.append(metric_line("majlesyar_maxmind_db_age_seconds", age_seconds))
    elif args.role == "origin":
        lines.append(metric_line("majlesyar_nginx_service_up", 1 if service_up("nginx") else 0))
        container_ok = docker_container_healthy(args.container_name)
        if container_ok is not None:
            lines.append(metric_line("majlesyar_app_container_up", 1 if container_ok else 0, {"container": args.container_name}))
        lines.append(metric_line("majlesyar_local_nginx_health_ok", 1 if http_ok(args.nginx_url) else 0))
        lines.append(metric_line("majlesyar_local_app_health_ok", 1 if http_ok(args.app_url) else 0))
    else:
        lines.append(metric_line("majlesyar_nginx_service_up", 1 if service_up("nginx") else 0))
        lines.append(metric_line("majlesyar_local_nginx_health_ok", 1 if http_ok(args.nginx_url) else 0))

    args.prom_out.parent.mkdir(parents=True, exist_ok=True)
    args.prom_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

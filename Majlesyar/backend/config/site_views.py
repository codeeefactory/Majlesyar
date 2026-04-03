from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_safe


def _read_file_text(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def _default_robots(sitemap_url: str) -> str:
    return "\n".join(
        [
            "# Robots.txt for Majlesyar",
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /checkout",
            "Disallow: /order/",
            "",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )


def _strip_unknown_robots_directives(content: str) -> str:
    lines = [
        line
        for line in content.splitlines()
        if not line.lstrip().lower().startswith("content-signal:")
    ]
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


@require_safe
def robots_txt(request) -> HttpResponse:
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    content = _read_file_text(
        [
            settings.FRONTEND_DIST_DIR / "robots.txt",
            settings.STATIC_ROOT / "robots.txt",
        ]
    )
    if content is None:
        content = _default_robots(sitemap_url)
    elif "Sitemap:" in content:
        lines = [
            f"Sitemap: {sitemap_url}" if line.strip().lower().startswith("sitemap:") else line
            for line in content.splitlines()
        ]
        content = "\n".join(lines) + ("\n" if not content.endswith("\n") else "")

    content = _strip_unknown_robots_directives(content)

    return HttpResponse(content, content_type="text/plain; charset=utf-8")


@require_safe
def sitemap_xml(request) -> HttpResponse:
    content = _read_file_text(
        [
            settings.FRONTEND_DIST_DIR / "sitemap.xml",
            settings.STATIC_ROOT / "sitemap.xml",
        ]
    )
    if content is None:
        content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>
"""
    return HttpResponse(content, content_type="application/xml; charset=utf-8")

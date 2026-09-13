from __future__ import annotations

import fnmatch

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponsePermanentRedirect


class LegacyViteAssetRedirectMiddleware:
    """Redirect old Vite /assets URLs to Django's /static/assets path."""

    _legacy_prefix = "/assets/"
    _static_prefix = "/static/assets/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self._legacy_prefix):
            suffix = request.get_full_path()[len(self._legacy_prefix) :]
            return HttpResponsePermanentRedirect(f"{self._static_prefix}{suffix}")
        return self.get_response(request)


class SensitivePathBlockMiddleware:
    """Fail closed for common probe paths so SPA fallback never masks sensitive-file checks."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exact_paths = {path.lower() for path in getattr(settings, "SENSITIVE_BLOCKED_PATHS", set())}
        self.glob_patterns = tuple(
            pattern.lower() for pattern in getattr(settings, "SENSITIVE_BLOCKED_PATH_GLOBS", ())
        )

    def __call__(self, request):
        path = request.path_info.lower()
        if path in self.exact_paths or any(fnmatch.fnmatch(path, pattern) for pattern in self.glob_patterns):
            return HttpResponse("Not found.", status=404, content_type="text/plain; charset=utf-8")
        return self.get_response(request)


class LoginRateLimitMiddleware:
    """Small edge-independent throttle for admin/JWT login POSTs."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.paths = {path.lower() for path in getattr(settings, "LOGIN_RATE_LIMIT_PATHS", set())}
        self.limit = int(getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 10))
        self.window = int(getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300))

    def _client_ip(self, request) -> str:
        for header in ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP"):
            value = request.META.get(header, "").strip()
            if value:
                return value
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def __call__(self, request):
        path = request.path_info.lower()
        if request.method == "POST" and path in self.paths:
            cache_key = f"login-rate:{path}:{self._client_ip(request)}"
            attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, attempts, self.window)
            if attempts > self.limit:
                response = HttpResponse(
                    "Too many login attempts. Try again later.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
                response.headers["Retry-After"] = str(self.window)
                return response
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Apply production security headers that scans require and Django does not cover fully."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        self.admin_csp = getattr(settings, "ADMIN_CONTENT_SECURITY_POLICY", "")
        self.permissions_policy = getattr(settings, "PERMISSIONS_POLICY", "")
        self.private_noindex_paths = tuple(
            path.rstrip("/").lower() for path in getattr(settings, "PRIVATE_NOINDEX_PATHS", ())
        )

    def __call__(self, request):
        response = self.get_response(request)
        csp = self.admin_csp if request.path_info.startswith("/majmanage/") else self.csp
        if csp:
            response.headers.setdefault("Content-Security-Policy", csp)
        if self.permissions_policy:
            response.headers.setdefault("Permissions-Policy", self.permissions_policy)
        response.headers.setdefault("X-Frame-Options", getattr(settings, "X_FRAME_OPTIONS", "DENY"))
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", getattr(settings, "SECURE_REFERRER_POLICY", "same-origin"))
        path = request.path_info.rstrip("/").lower() or "/"
        if any(path == private_path or path.startswith(f"{private_path}/") for private_path in self.private_noindex_paths):
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
        return response


class StripCrawlerDirectivesMiddleware:
    """Remove non-standard crawler directives that trigger validator errors."""

    _protected_paths = {"/robots.txt", "/sitemap.xml", "/llms.txt"}
    _headers_to_strip = {"Content-Signal"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path in self._protected_paths:
            for header in self._headers_to_strip:
                response.headers.pop(header, None)
        return response


class OptimizedMediaCacheMiddleware:
    """Cache product media; hashed optimized variants get immutable caching."""

    _optimized_media_prefix = "/media/products/optimized/"
    _product_media_prefix = "/media/products/"
    _immutable_cache_value = "public, max-age=31536000, immutable"
    _product_cache_value = "public, max-age=604800, stale-while-revalidate=86400"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self._optimized_media_prefix):
            response.headers["Cache-Control"] = self._immutable_cache_value
        elif request.path.startswith(self._product_media_prefix):
            response.headers["Cache-Control"] = self._product_cache_value
        return response

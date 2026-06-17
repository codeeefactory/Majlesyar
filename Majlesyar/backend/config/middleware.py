from __future__ import annotations

from django.http import HttpResponsePermanentRedirect


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


class StripCrawlerDirectivesMiddleware:
    """Remove non-standard crawler directives that trigger validator errors."""

    _protected_paths = {"/robots.txt", "/sitemap.xml"}
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

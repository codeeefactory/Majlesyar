from __future__ import annotations


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
    """Cache hashed product variants aggressively without affecting mutable media."""

    _media_prefix = "/media/products/optimized/"
    _cache_value = "public, max-age=31536000, immutable"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self._media_prefix):
            response.headers["Cache-Control"] = self._cache_value
        return response

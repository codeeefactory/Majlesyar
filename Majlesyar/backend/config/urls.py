import os
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from config.site_views import (
    NoCacheTemplateView,
    favicon_redirect,
    forced_not_found,
    llms_txt,
    robots_txt,
    sitemap_xml,
    verification_6285703_txt,
    verification_8583454_txt,
)
from drf_spectacular.views import SpectacularAPIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from telegram_bot.views import TelegramWebhookAPIView
from catalog.admin_views import purge_cloudflare_cache_view

urlpatterns = [
    re_path(
        r"^media/products/optimized/aza/8b380b32e31e/(?:320|480|960)/پک(?: |%20)عزا\.avif$",
        forced_not_found,
        name="removed-pack-aza-image",
    ),
    path(
        "majmanage/cloudflare/purge/",
        admin.site.admin_view(purge_cloudflare_cache_view),
        name="admin-cloudflare-purge",
    ),
    path("majmanage/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", NoCacheTemplateView.as_view(template_name="api_docs.html"), name="api-docs"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/", include("blog.urls")),
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("site_settings.urls")),
    path("api/v1/", include("orders.urls")),
    path("api/v1/", include("operations.urls")),
    path("api/v1/maps-scraper/", include("google_maps_scraper.urls")),
    path("api/v1/", include("telegram_bot.urls")),
    path(settings.TELEGRAM_BOT["WEBHOOK_PATH"], TelegramWebhookAPIView.as_view(), name="telegram-webhook"),
    path("robots.txt", robots_txt, name="robots-txt"),
    path("llms.txt", llms_txt, name="llms-txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
    path("6285703.txt", verification_6285703_txt, name="verification-6285703-txt"),
    path("8583454.txt", verification_8583454_txt, name="verification-8583454-txt"),
    path("order", RedirectView.as_view(url="/track", permanent=False), name="order-shortcut"),
    path("order/", RedirectView.as_view(url="/track", permanent=False), name="order-shortcut-slash"),
]

if (settings.BASE_DIR / "frontend_dist" / "index.html").exists():
    urlpatterns += [
        path("favicon.ico", favicon_redirect, name="favicon-redirect"),
        re_path(
            r"^(?!api/|majmanage/|media/|static/).*$",
            NoCacheTemplateView.as_view(template_name="index.html"),
            name="frontend-app",
        ),
    ]

serve_media = os.getenv("SERVE_MEDIA", "1").strip().lower() in {"1", "true", "yes", "on"}
if settings.DEBUG or serve_media:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

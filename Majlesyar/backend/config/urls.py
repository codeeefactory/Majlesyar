import os
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from config.site_views import favicon_redirect, robots_txt, sitemap_xml
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from telegram_bot.views import TelegramWebhookAPIView

urlpatterns = [
    path("majmanage/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("site_settings.urls")),
    path("api/v1/", include("orders.urls")),
    path("api/v1/", include("operations.urls")),
    path("api/v1/", include("telegram_bot.urls")),
    path(settings.TELEGRAM_BOT["WEBHOOK_PATH"], TelegramWebhookAPIView.as_view(), name="telegram-webhook"),
    path("robots.txt", robots_txt, name="robots-txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
]

if (settings.BASE_DIR / "frontend_dist" / "index.html").exists():
    urlpatterns += [
        path("favicon.ico", favicon_redirect, name="favicon-redirect"),
        re_path(
            r"^(?!api/|admin/|media/|static/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="frontend-app",
        ),
    ]

serve_media = os.getenv("SERVE_MEDIA", "1").strip().lower() in {"1", "true", "yes", "on"}
if settings.DEBUG or serve_media:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

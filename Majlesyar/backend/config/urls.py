from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from config.site_views import robots_txt, sitemap_xml
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("site_settings.urls")),
    path("api/v1/", include("orders.urls")),
    path("robots.txt", robots_txt, name="robots-txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
]

if (settings.BASE_DIR / "frontend_dist" / "index.html").exists():
    urlpatterns += [
        path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=False)),
        re_path(
            r"^(?!api/|admin/|media/|static/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="frontend-app",
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.urls import path

from .views import AdminSiteSettingRetrieveUpdateAPIView, PingAPIView, SiteSettingRetrieveAPIView

urlpatterns = [
    path("settings/", SiteSettingRetrieveAPIView.as_view(), name="site-setting-detail"),
    path("admin/site-settings/", AdminSiteSettingRetrieveUpdateAPIView.as_view(), name="admin-site-setting-detail"),
    path("ping/", PingAPIView.as_view(), name="site-ping"),
]

from django.urls import path

from .views import PingAPIView, SiteSettingRetrieveAPIView

urlpatterns = [
    path("settings/", SiteSettingRetrieveAPIView.as_view(), name="site-setting-detail"),
    path("ping/", PingAPIView.as_view(), name="site-ping"),
]

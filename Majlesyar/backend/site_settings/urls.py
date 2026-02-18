from django.urls import path

from .views import SiteSettingRetrieveAPIView

urlpatterns = [
    path("settings/", SiteSettingRetrieveAPIView.as_view(), name="site-setting-detail"),
]

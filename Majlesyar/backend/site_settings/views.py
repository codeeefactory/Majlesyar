from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSetting
from .serializers import SiteSettingSerializer


class SiteSettingRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = SiteSettingSerializer

    def get_object(self):
        return SiteSetting.load()


class PingAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        response = Response(
            {
                "ok": True,
                "server_time": timezone.now().isoformat(),
            }
        )
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

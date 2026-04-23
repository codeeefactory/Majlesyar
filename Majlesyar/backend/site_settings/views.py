from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.permissions import IsStaffUser
from .models import SiteSetting
from .serializers import SiteSettingSerializer, SiteSettingWriteSerializer


class SiteSettingRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = SiteSettingSerializer

    def get_object(self):
        return SiteSetting.load()


class AdminSiteSettingRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStaffUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return SiteSetting.load()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return SiteSettingWriteSerializer
        return SiteSettingSerializer


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

from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, serializers
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

    @extend_schema(
        responses=inline_serializer(
            name="PingResponse",
            fields={
                "ok": serializers.BooleanField(),
                "server_time": serializers.DateTimeField(),
            },
        )
    )
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


class HealthAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        responses=inline_serializer(
            name="HealthResponse",
            fields={
                "ok": serializers.BooleanField(),
                "server_time": serializers.DateTimeField(),
                "checks": serializers.DictField(child=serializers.JSONField()),
            },
        )
    )
    def get(self, request):
        database_ok = True
        database_error = None

        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # pragma: no cover - exercised in tests via patching.
            database_ok = False
            database_error = exc.__class__.__name__

        payload = {
            "ok": database_ok,
            "server_time": timezone.now().isoformat(),
            "checks": {
                "database": {
                    "ok": database_ok,
                }
            },
        }
        if database_error:
            payload["checks"]["database"]["error"] = database_error

        response = Response(payload, status=200 if database_ok else 503)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

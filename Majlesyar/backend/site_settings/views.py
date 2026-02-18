from rest_framework import generics

from .models import SiteSetting
from .serializers import SiteSettingSerializer


class SiteSettingRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = SiteSettingSerializer

    def get_object(self):
        return SiteSetting.load()

# Create your views here.

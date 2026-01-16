from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import CustomRegion
from locations.serializers import RegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class CustomRegionDetailAPIView(RetrieveAPIView):
    queryset = CustomRegion.objects.filter(deleted_at__isnull=True)
    serializer_class = RegionReadSerializerV1
    error_class = InvalidLocationData

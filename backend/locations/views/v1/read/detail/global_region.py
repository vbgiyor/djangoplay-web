from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import GlobalRegion
from locations.serializers import GlobalRegionReadSerializerV1


@extend_schema(tags=["Locations: Continent"])
class GlobalRegionDetailAPIView(RetrieveAPIView):
    queryset = GlobalRegion.objects.filter(deleted_at__isnull=True)
    serializer_class = GlobalRegionReadSerializerV1
    error_class = InvalidLocationData

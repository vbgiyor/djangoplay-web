from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import CustomSubRegion
from locations.serializers import SubRegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class CustomSubRegionDetailAPIView(RetrieveAPIView):
    queryset = CustomSubRegion.objects.filter(deleted_at__isnull=True)
    serializer_class = SubRegionReadSerializerV1
    error_class = InvalidLocationData

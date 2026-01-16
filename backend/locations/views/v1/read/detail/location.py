from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import Location
from locations.serializers import LocationReadSerializerV1


@extend_schema(tags=["Locations: Location"])
class LocationDetailAPIView(RetrieveAPIView):
    queryset = Location.objects.filter(deleted_at__isnull=True)
    serializer_class = LocationReadSerializerV1
    error_class = InvalidLocationData

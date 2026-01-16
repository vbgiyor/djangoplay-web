from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import Location
from locations.serializers import LocationReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class LocationHistoryAPIView(BaseHistoryListAPIView):
    queryset = Location.objects.all()
    history_queryset = Location.history.all()
    serializer_class = LocationReadSerializerV1

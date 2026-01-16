from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import CustomRegion
from locations.serializers import RegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class CustomRegionHistoryAPIView(BaseHistoryListAPIView):
    queryset = CustomRegion.objects.all()
    history_queryset = CustomRegion.history.all()
    serializer_class = RegionReadSerializerV1

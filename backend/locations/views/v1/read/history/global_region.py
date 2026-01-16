from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import GlobalRegion
from locations.serializers import GlobalRegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class GlobalRegionHistoryAPIView(BaseHistoryListAPIView):
    queryset = GlobalRegion.objects.all()
    history_queryset = GlobalRegion.history.all()
    serializer_class = GlobalRegionReadSerializerV1

from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import CustomSubRegion
from locations.serializers import SubRegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class CustomSubRegionHistoryAPIView(BaseHistoryListAPIView):
    queryset = CustomSubRegion.objects.all()
    history_queryset = CustomSubRegion.history.all()
    serializer_class = SubRegionReadSerializerV1

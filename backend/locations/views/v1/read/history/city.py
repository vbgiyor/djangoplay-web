from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import CustomCity
from locations.serializers import CityReadSerializerV1


@extend_schema(tags=["Locations: City"])
class CustomCityHistoryAPIView(BaseHistoryListAPIView):
    queryset = CustomCity.objects.all()
    history_queryset = CustomCity.history.all()
    serializer_class = CityReadSerializerV1

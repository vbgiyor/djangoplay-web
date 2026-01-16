from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from locations.models import CustomCountry
from locations.serializers import CountryReadSerializerV1


@extend_schema(tags=["Locations: Country"])
class CustomCountryHistoryAPIView(BaseHistoryListAPIView):
    queryset = CustomCountry.objects.all()
    history_queryset = CustomCountry.history.all()
    serializer_class = CountryReadSerializerV1

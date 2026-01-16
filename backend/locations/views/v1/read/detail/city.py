from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import CustomCity
from locations.serializers import CityReadSerializerV1


@extend_schema(tags=["Locations: City"])
class CityDetailAPIView(RetrieveAPIView):
    queryset = CustomCity.objects.filter(deleted_at__isnull=True)
    serializer_class = CityReadSerializerV1
    error_class = InvalidLocationData

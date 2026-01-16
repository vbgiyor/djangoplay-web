from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from locations.exceptions import InvalidLocationData
from locations.models import CustomCountry
from locations.serializers import CountryReadSerializerV1


@extend_schema(tags=["Locations: Country"])
class CustomCountryDetailAPIView(RetrieveAPIView):
    queryset = CustomCountry.objects.filter(deleted_at__isnull=True)
    serializer_class = CountryReadSerializerV1
    error_class = InvalidLocationData

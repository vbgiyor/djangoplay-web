from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination

from locations.exceptions import InvalidLocationData
from locations.models import Location
from locations.serializers import LocationReadSerializerV1


@extend_schema(tags=["Locations: Geolocation"])
class LocationListAPIView(BaseListAPIView):
    queryset = Location.objects.filter(deleted_at__isnull=True)
    serializer_class = LocationReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["city", "postal_code"]
    ordering_fields = ["id"]
    search_fields = ["postal_code", "street_address"]
    error_class = InvalidLocationData

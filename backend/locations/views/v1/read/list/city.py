from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination

from locations.exceptions import InvalidLocationData
from locations.models import CustomCity
from locations.serializers import CityReadSerializerV1


@extend_schema(tags=["Locations: City"])
class CityListAPIView(BaseListAPIView):
    queryset = CustomCity.objects.filter(deleted_at__isnull=True)
    serializer_class = CityReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "subregion"]
    ordering_fields = ["id", "name"]
    search_fields = ["name"]
    error_class = InvalidLocationData

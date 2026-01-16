from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.filters import (
    DateRangeFilterMixin,
    NameSearchFilterMixin,
)
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from locations.exceptions import InvalidLocationData
from locations.models import CustomCountry
from locations.serializers import CountryReadSerializerV1


@extend_schema(tags=["Locations: Country"])
class CountryListAPIView(
        DateRangeFilterMixin,
        NameSearchFilterMixin,
        BaseListAPIView
    ):
    queryset = CustomCountry.objects.filter(deleted_at__isnull=True)
    serializer_class = CountryReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "name",
        "country_code",
        "currency_code",
        "population",
        "country_languages",
    ]
    ordering_fields = ["id", "name", "population"]
    search_fields = ["name", "country_code"]
    throttle_classes = [CustomThrottle]
    error_class = InvalidLocationData

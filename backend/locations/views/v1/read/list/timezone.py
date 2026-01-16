from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseFilteredListAPIView
from utilities.api.pagination import StandardResultsSetPagination

from locations.models import Timezone
from locations.serializers import TimezoneReadSerializerV1


@extend_schema(tags=["Locations: Timezone"])
class TimezoneListAPIView(BaseFilteredListAPIView):
    queryset = Timezone.objects.filter(deleted_at__isnull=True)
    serializer_class = TimezoneReadSerializerV1
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["timezone_id", "country_code"]
    ordering_fields = ["timezone_id"]
    search_fields = ["timezone_id", "display_name"]

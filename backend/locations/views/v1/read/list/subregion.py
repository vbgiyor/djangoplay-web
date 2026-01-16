from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from locations.exceptions import InvalidLocationData
from locations.models import CustomSubRegion
from locations.serializers import SubRegionReadSerializerV1


@extend_schema(tags=["Locations: Subregion"])
class SubRegionListAPIView(BaseListAPIView):
    queryset = CustomSubRegion.objects.filter(deleted_at__isnull=True)
    serializer_class =SubRegionReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    filterset_fields = [
        "name",
        "code",
        "region",
    ]
    ordering_fields = [
        "id",
        "name",
    ]
    search_fields = [
        "name",
        "code",
    ]
    error_class = InvalidLocationData

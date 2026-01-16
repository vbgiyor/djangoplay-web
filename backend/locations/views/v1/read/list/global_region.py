from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from locations.exceptions import InvalidLocationData
from locations.models import GlobalRegion
from locations.serializers import GlobalRegionReadSerializerV1


@extend_schema(tags=["Locations: Region"])
class GlobalRegionListAPIView(BaseListAPIView):
    queryset = GlobalRegion.objects.filter(deleted_at__isnull=True)
    serializer_class = GlobalRegionReadSerializerV1
    error_class = InvalidLocationData
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    throttle_classes = [CustomThrottle]
    filterset_fields =[
        "name",
        "code",
    ]
    ordering_fields = [
        "id",
        "name"
    ]
    search_fields = [
        "name",
        "code"
    ]

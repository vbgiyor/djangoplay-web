from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from industries.exceptions import InvalidIndustryData
from industries.models import Industry
from industries.serializers.v1.read import IndustryReadSerializerV1


@extend_schema(tags=["Industries"])
class IndustryListAPIView(BaseListAPIView):
    queryset = Industry.objects.filter(deleted_at__isnull=True)
    serializer_class = IndustryReadSerializerV1
    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    error_class = InvalidIndustryData

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["code", "level", "sector", "parent"]
    ordering_fields = ["id", "code", "level"]
    search_fields = ["code", "description"]

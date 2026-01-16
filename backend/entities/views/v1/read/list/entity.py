from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from entities.exceptions import EntityValidationError
from entities.models import Entity
from entities.serializers.v1.read import EntityReadSerializerV1
from utilities.api.generic_views import BaseListAPIView
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle


@extend_schema(tags=["Business"])
class EntityListAPIView(BaseListAPIView):
    queryset = Entity.objects.filter(deleted_at__isnull=True, is_active=True)
    serializer_class = EntityReadSerializerV1
    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    error_class = EntityValidationError

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["entity_type", "status", "industry", "parent"]
    ordering_fields = ["name", "created_at"]
    search_fields = ["name", "slug"]

import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet
from utilities.api.rate_limits import CustomThrottle

from locations.exceptions import InvalidLocationData
from locations.models import GlobalRegion
from locations.serializers.v1.read import GlobalRegionReadSerializerV1
from locations.serializers.v1.write import GlobalRegionWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: Continent"])
class GlobalRegionViewSet(BaseViewSet):
    queryset = GlobalRegion.objects.filter(deleted_at__isnull=True)

    read_serializer_class = GlobalRegionReadSerializerV1
    write_serializer_class = GlobalRegionWriteSerializerV1

    throttle_classes = [CustomThrottle]
    error_class = InvalidLocationData
    filterset_fields = ["name", "code"]
    ordering_fields = ["id", "name"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            search = self.request.query_params.get("search")
            if search:
                qs = qs.filter(
                    Q(name__trigram_similar=search)
                    | Q(code__trigram_similar=search)
                )
        return qs.order_by("name")

    @BaseSchema.get_common_schema(
        "List Global Regions",
        "List all global regions.",
        GlobalRegionReadSerializerV1,
        "locations_global_region_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve Global Region",
        "Retrieve a global region.",
        GlobalRegionReadSerializerV1,
        "locations_global_region_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create Global Region",
        "Create a new global region.",
        GlobalRegionWriteSerializerV1,
        GlobalRegionReadSerializerV1,
        "locations_global_region_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update Global Region",
        "Update a global region.",
        GlobalRegionWriteSerializerV1,
        GlobalRegionReadSerializerV1,
        "locations_global_region_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update Global Region",
        "Partially update a global region.",
        GlobalRegionWriteSerializerV1,
        GlobalRegionReadSerializerV1,
        "locations_global_region_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete Global Region",
        "Soft delete a global region.",
        GlobalRegionReadSerializerV1,
        "locations_global_region_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

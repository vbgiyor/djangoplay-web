import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet

from locations.exceptions import InvalidLocationData
from locations.models import CustomSubRegion
from locations.serializers.v1.read import SubRegionReadSerializerV1
from locations.serializers.v1.write import SubRegionWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: Subregion"])
class CustomSubRegionViewSet(BaseViewSet):
    queryset = CustomSubRegion.objects.filter(deleted_at__isnull=True)

    read_serializer_class = SubRegionReadSerializerV1
    write_serializer_class = SubRegionWriteSerializerV1

    error_class = InvalidLocationData
    filterset_fields = ["name", "code", "region"]
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
        "List Subregions",
        "List all subregions.",
        SubRegionReadSerializerV1,
        "locations_subregion_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve Subregion",
        "Retrieve a subregion.",
        SubRegionReadSerializerV1,
        "locations_subregion_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create Subregion",
        "Create a new subregion.",
        SubRegionWriteSerializerV1,
        SubRegionReadSerializerV1,
        "locations_subregion_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update Subregion",
        "Update a subregion.",
        SubRegionWriteSerializerV1,
        SubRegionReadSerializerV1,
        "locations_subregion_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update Subregion",
        "Partially update a subregion.",
        SubRegionWriteSerializerV1,
        SubRegionReadSerializerV1,
        "locations_subregion_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete Subregion",
        "Soft delete a subregion.",
        SubRegionReadSerializerV1,
        "locations_subregion_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

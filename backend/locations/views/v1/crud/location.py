import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet

from locations.exceptions import InvalidLocationData
from locations.models import Location
from locations.serializers.v1.read import LocationReadSerializerV1
from locations.serializers.v1.write import LocationWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: Geolocation"])
class LocationViewSet(BaseViewSet):
    queryset = Location.objects.filter(deleted_at__isnull=True)

    read_serializer_class = LocationReadSerializerV1
    write_serializer_class = LocationWriteSerializerV1

    error_class = InvalidLocationData
    filterset_fields = ["city", "postal_code"]
    ordering_fields = ["id"]
    search_fields = ["postal_code", "street_address"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            search = self.request.query_params.get("search")
            if search:
                qs = qs.filter(
                    Q(street_address__trigram_similar=search)
                    | Q(postal_code__trigram_similar=search)
                )
        return qs

    @BaseSchema.get_common_schema(
        "List Locations",
        "List all locations.",
        LocationReadSerializerV1,
        "locations_location_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve Location",
        "Retrieve a location.",
        LocationReadSerializerV1,
        "locations_location_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create Location",
        "Create a new location.",
        LocationWriteSerializerV1,
        LocationReadSerializerV1,
        "locations_location_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update Location",
        "Update a location.",
        LocationWriteSerializerV1,
        LocationReadSerializerV1,
        "locations_location_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update Location",
        "Partially update a location.",
        LocationWriteSerializerV1,
        LocationReadSerializerV1,
        "locations_location_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete Location",
        "Soft delete a location.",
        LocationReadSerializerV1,
        "locations_location_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet

from locations.exceptions import InvalidLocationData
from locations.models import Timezone
from locations.serializers.v1.read import TimezoneReadSerializerV1
from locations.serializers.v1.write import TimezoneWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: Timezone"])
class TimezoneViewSet(BaseViewSet):
    queryset = Timezone.objects.filter(deleted_at__isnull=True)

    read_serializer_class = TimezoneReadSerializerV1
    write_serializer_class = TimezoneWriteSerializerV1

    error_class = InvalidLocationData
    filterset_fields = ["timezone_id", "raw_offset"]
    ordering_fields = ["timezone_id"]
    search_fields = ["timezone_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            search = self.request.query_params.get("search")
            if search:
                qs = qs.filter(name__trigram_similar=search)
        return qs.order_by("timezone_id")

    @BaseSchema.get_common_schema(
        "List Timezones",
        "List all timezones.",
        TimezoneReadSerializerV1,
        "locations_timezone_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve Timezone",
        "Retrieve a timezone.",
        TimezoneReadSerializerV1,
        "locations_timezone_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create Timezone",
        "Create a new timezone.",
        TimezoneWriteSerializerV1,
        TimezoneReadSerializerV1,
        "locations_timezone_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update Timezone",
        "Update a timezone.",
        TimezoneWriteSerializerV1,
        TimezoneReadSerializerV1,
        "locations_timezone_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update Timezone",
        "Partially update a timezone.",
        TimezoneWriteSerializerV1,
        TimezoneReadSerializerV1,
        "locations_timezone_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete Timezone",
        "Soft delete a timezone.",
        TimezoneReadSerializerV1,
        "locations_timezone_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

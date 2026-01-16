import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet

from locations.exceptions import InvalidLocationData
from locations.models import CustomCity
from locations.serializers.v1.read import CityReadSerializerV1
from locations.serializers.v1.write import CityWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: City"])
class CustomCityViewSet(BaseViewSet):
    queryset = CustomCity.objects.filter(deleted_at__isnull=True)

    read_serializer_class = CityReadSerializerV1
    write_serializer_class = CityWriteSerializerV1

    error_class = InvalidLocationData
    filterset_fields = ["name", "subregion"]
    ordering_fields = ["id", "name"]
    search_fields = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            search = self.request.query_params.get("search")
            if search:
                qs = qs.filter(name__trigram_similar=search)
        return qs.order_by("name")

    @BaseSchema.get_common_schema(
        "List Cities",
        "List all cities.",
        CityReadSerializerV1,
        "locations_city_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve City",
        "Retrieve a city.",
        CityReadSerializerV1,
        "locations_city_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create City",
        "Create a new city.",
        CityWriteSerializerV1,
        CityReadSerializerV1,
        "locations_city_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update City",
        "Update a city.",
        CityWriteSerializerV1,
        CityReadSerializerV1,
        "locations_city_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update City",
        "Partially update a city.",
        CityWriteSerializerV1,
        CityReadSerializerV1,
        "locations_city_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete City",
        "Soft delete a city.",
        CityReadSerializerV1,
        "locations_city_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

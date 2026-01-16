import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from utilities.api.generic_viewsets import BaseViewSet
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from locations.exceptions import InvalidLocationData
from locations.models import CustomCountry
from locations.serializers.v1.read import CountryReadSerializerV1
from locations.serializers.v1.write import CountryWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Locations: Country"])
class CustomCountryViewSet(BaseViewSet):
    queryset = CustomCountry.objects.filter(deleted_at__isnull=True)

    # 🔑 Serializer resolution (used by SerializerByActionMixin)
    read_serializer_class = CountryReadSerializerV1
    write_serializer_class = CountryWriteSerializerV1

    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    error_class = InvalidLocationData

    filterset_fields = [
        "name",
        "country_code",
        "currency_code",
        "country_languages",
    ]
    ordering_fields = ["id", "name", "population"]
    search_fields = ["name", "asciiname", "alternatenames", "country_code"]

    # ------------------------------------------------------------------
    # Queryset logic
    # ------------------------------------------------------------------
    def get_queryset(self):
        qs = super().get_queryset()

        if self.action != "list":
            return qs

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__trigram_similar=search)
                | Q(asciiname__trigram_similar=search)
                | Q(alternatenames__trigram_similar=search)
                | Q(country_code__iexact=search)
            )

        return qs.order_by("name")

    # ------------------------------------------------------------------
    # READ OPERATIONS
    # ------------------------------------------------------------------
    @BaseSchema.get_common_schema(
        summary="List Countries",
        description="List all countries.",
        serializer_class=CountryReadSerializerV1,
        operation_id="locations_country_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Retrieve Country",
        description="Retrieve a single country by ID.",
        serializer_class=CountryReadSerializerV1,
        operation_id="locations_country_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # WRITE OPERATIONS
    # ------------------------------------------------------------------
    @BaseSchema.get_write_schema(
        summary="Create Country",
        description="Create a new country.",
        request_serializer=CountryWriteSerializerV1,
        response_serializer=CountryReadSerializerV1,
        operation_id="locations_country_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Update Country",
        description="Update a country.",
        request_serializer=CountryWriteSerializerV1,
        response_serializer=CountryReadSerializerV1,
        operation_id="locations_country_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Partial Update Country",
        description="Partially update a country.",
        request_serializer=CountryWriteSerializerV1,
        response_serializer=CountryReadSerializerV1,
        operation_id="locations_country_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Delete Country",
        description="Soft delete a country.",
        serializer_class=CountryReadSerializerV1,
        operation_id="locations_country_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

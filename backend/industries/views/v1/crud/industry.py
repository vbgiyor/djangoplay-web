import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from utilities.api.generic_viewsets import BaseViewSet
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from industries.exceptions import InvalidIndustryData
from industries.models import Industry
from industries.serializers.v1.read import IndustryReadSerializerV1
from industries.serializers.v1.write import IndustryWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Industries"])
class IndustryViewSet(BaseViewSet):
    queryset = Industry.objects.filter(deleted_at__isnull=True)

    read_serializer_class = IndustryReadSerializerV1
    write_serializer_class = IndustryWriteSerializerV1

    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    error_class = InvalidIndustryData

    filterset_fields = ["code", "level", "sector", "parent"]
    ordering_fields = ["id", "code", "level"]
    search_fields = ["code", "description"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            search = self.request.query_params.get("search")
            if search:
                qs = qs.filter(
                    Q(code__icontains=search)
                    | Q(description__trigram_similar=search)
                )
        return qs.order_by("code")

    @BaseSchema.get_common_schema(
        "List Industries",
        "List all industries.",
        IndustryReadSerializerV1,
        "industries_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Retrieve Industry",
        "Retrieve an industry.",
        IndustryReadSerializerV1,
        "industries_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Create Industry",
        "Create an industry.",
        IndustryWriteSerializerV1,
        IndustryReadSerializerV1,
        "industries_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Update Industry",
        "Update an industry.",
        IndustryWriteSerializerV1,
        IndustryReadSerializerV1,
        "industries_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        "Partial Update Industry",
        "Partially update an industry.",
        IndustryWriteSerializerV1,
        IndustryReadSerializerV1,
        "industries_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        "Delete Industry",
        "Soft delete an industry.",
        IndustryReadSerializerV1,
        "industries_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

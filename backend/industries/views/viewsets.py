# industries/views/viewsets.py
import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from utilities.api.generic_viewsets import BaseViewSet
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

from industries.exceptions import InvalidIndustryData
from industries.models import Industry
from industries.serializers import IndustryReadSerializerV1, IndustryWriteSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Industries"])
class IndustryViewSet(BaseViewSet):
    queryset = Industry.objects.filter(deleted_at__isnull=True)

    # 🔑 REQUIRED BY BaseViewSet
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

        if self.action != "list":
            return qs

        params = self.request.query_params
        search = params.get("search")

        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(description__trigram_similar=search)
            )

        return qs.order_by("code")

    # ---------------- READ ----------------
    @BaseSchema.get_common_schema(
        summary="List Industries",
        description="List all industries.",
        serializer_class=IndustryReadSerializerV1,
        operation_id="industries_list",
        many=True,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Retrieve Industry",
        description="Retrieve an industry by ID.",
        serializer_class=IndustryReadSerializerV1,
        operation_id="industries_retrieve",
        many=False,
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ---------------- WRITE ----------------
    @BaseSchema.get_write_schema(
        summary="Create Industry",
        description="Create a new industry.",
        request_serializer=IndustryWriteSerializerV1,
        response_serializer=IndustryReadSerializerV1,
        operation_id="industries_create",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Update Industry",
        description="Update an industry.",
        request_serializer=IndustryWriteSerializerV1,
        response_serializer=IndustryReadSerializerV1,
        operation_id="industries_update",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Partial Update Industry",
        description="Partially update an industry.",
        request_serializer=IndustryWriteSerializerV1,
        response_serializer=IndustryReadSerializerV1,
        operation_id="industries_partial_update",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Delete Industry",
        description="Soft delete an industry.",
        serializer_class=IndustryReadSerializerV1,
        operation_id="industries_delete",
        many=False,
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

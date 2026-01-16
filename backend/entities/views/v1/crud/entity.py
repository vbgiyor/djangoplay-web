import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from entities.exceptions import EntityValidationError
from entities.models import Entity
from entities.serializers.v1.read import EntityReadSerializerV1
from entities.serializers.v1.write import EntityWriteSerializerV1
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from utilities.api.generic_viewsets import BaseViewSet
from utilities.api.pagination import StandardResultsSetPagination
from utilities.api.rate_limits import CustomThrottle

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Business"])
class EntityViewSet(BaseViewSet):
    queryset = Entity.objects.filter(deleted_at__isnull=True, is_active=True)

    read_serializer_class = EntityReadSerializerV1
    write_serializer_class = EntityWriteSerializerV1

    pagination_class = StandardResultsSetPagination
    throttle_classes = [CustomThrottle]
    error_class = EntityValidationError

    filterset_fields = [
        "entity_type",
        "status",
        "industry",
        "default_address",
        "parent",
    ]
    ordering_fields = ["name", "created_at", "updated_at"]
    search_fields = ["name", "slug", "registration_number", "website"]

    def get_queryset(self):
        qs = super().get_queryset()

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__trigram_similar=search)
                | Q(slug__trigram_similar=search)
                | Q(registration_number__trigram_similar=search)
                | Q(website__trigram_similar=search)
            )

        return qs.select_related(
            "industry",
            "default_address",
            "parent",
            "created_by",
            "updated_by",
        ).prefetch_related("children")

    # ---------------- READ ----------------

    @BaseSchema.get_common_schema(
        summary="List Entities",
        description="List entities.",
        serializer_class=EntityReadSerializerV1,
        operation_id="entities_list",
        many=True,
    )
    def list(self, request: Request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Retrieve Entity",
        description="Retrieve an entity.",
        serializer_class=EntityReadSerializerV1,
        operation_id="entities_retrieve",
        many=False,
    )
    def retrieve(self, request: Request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # ---------------- WRITE ----------------

    @BaseSchema.get_write_schema(
        summary="Create Entity",
        description="Create an entity.",
        request_serializer=EntityWriteSerializerV1,
        response_serializer=EntityReadSerializerV1,
        operation_id="entities_create",
    )
    def create(self, request: Request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Update Entity",
        description="Update an entity.",
        request_serializer=EntityWriteSerializerV1,
        response_serializer=EntityReadSerializerV1,
        operation_id="entities_update",
    )
    def update(self, request: Request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @BaseSchema.get_write_schema(
        summary="Partial Update Entity",
        description="Partially update an entity.",
        request_serializer=EntityWriteSerializerV1,
        response_serializer=EntityReadSerializerV1,
        operation_id="entities_partial_update",
    )
    def partial_update(self, request: Request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @BaseSchema.get_common_schema(
        summary="Delete Entity",
        description="Soft delete an entity.",
        serializer_class=EntityReadSerializerV1,
        operation_id="entities_delete",
        many=False,
    )
    def destroy(self, request: Request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

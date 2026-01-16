
import hashlib
import json
import logging

from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from policyengine.components.permissions import get_action_based_permissions
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from utilities.api.generic_api_exceptions import GenericAPIError
from utilities.api.rate_limits import CustomThrottle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Base List API
# ---------------------------------------------------------------------
class BaseListAPIView(ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [CustomThrottle]
    filter_backends = []
    filterset_fields = None
    cache_timeout = 172800

    error_class = GenericAPIError

    def get_filterset_class(self):
        if getattr(self, "swagger_fake_view", False):
            return None
        return super().get_filterset_class()

    def get_queryset(self):
        qs = super().get_queryset()
        assert qs.model is not None, f"{self.__class__.__name__} returned queryset without model"
        return qs

    def get_permissions(self):
        return get_action_based_permissions(self.permission_classes)

    def get(self, request: Request, *args, **kwargs) -> Response:
        try:
            query_params = json.dumps(request.query_params.dict(), sort_keys=True)
            # cache_key = f"{self.__class__.__name__.lower()}_{request.user.id}_{hash(query_params)}"
            params_hash = hashlib.sha256(query_params.encode()).hexdigest()

            cache_key = f"{self.__class__.__name__.lower()}_{request.user.id}_{params_hash}"

            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data)

            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                data = self.get_paginated_response(serializer.data).data
            else:
                serializer = self.get_serializer(queryset, many=True)
                data = {
                    "count": queryset.count(),
                    "next": None,
                    "previous": None,
                    "results": serializer.data,
                }

            cache.set(cache_key, data, timeout=self.cache_timeout)
            return Response(data)

        except DRFValidationError as e:
            return Response(
                {"code": "invalid_fields", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("List API failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to list records",
                    code="invalid_location_data",
                    details={"operation": "list"},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------
# Base Detail API
# ---------------------------------------------------------------------
class BaseDetailAPIView(RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [CustomThrottle]
    cache_timeout = 86400

    error_class = GenericAPIError
    swagger_tags = ["Generic Detail"]

    def get_permissions(self):
        return get_action_based_permissions(self.permission_classes)

    @extend_schema(
        tags=swagger_tags,
        summary="Retrieve details",
        description="Get details of a specific resource by ID.",
        responses={
            200: OpenApiResponse(description="Success"),
            404: OpenApiResponse(description="Not found"),
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    def get(self, request: Request, pk: int, *args, **kwargs) -> Response:
        try:
            pk = int(pk)
        except ValueError:
            return Response(
                self.error_class(
                    "Invalid ID",
                    code="invalid_fields",
                    details={"field": "pk", "value": pk},
                ).to_dict(),
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"{self.__class__.__name__.lower()}_{pk}_{request.user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data
            cache.set(cache_key, data, timeout=self.cache_timeout)
            return Response(data)

        except self.queryset.model.DoesNotExist:
            return Response(
                {"detail": f"{self.queryset.model.__name__} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.error("Detail API failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to retrieve record",
                    code="retrieve_error",
                    details={"operation": "retrieve", "pk": pk},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------
# Filtered List API
# ---------------------------------------------------------------------
class BaseFilteredListAPIView(BaseListAPIView):
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        qs = super().get_queryset()
        assert (
            self.filterset_fields is not None
            or getattr(self, "filterset_class", None) is not None
        ), f"{self.__class__.__name__} requires filterset_fields or filterset_class"
        return qs


# ---------------------------------------------------------------------
# Bulk API
# ---------------------------------------------------------------------
class BaseBulkAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [CustomThrottle]
    error_class = GenericAPIError

    def get_permissions(self):
        return get_action_based_permissions(self.permission_classes)

    def put(self, request, *args, **kwargs):
        try:
            return self.bulk_update(request)

        except DRFValidationError as e:
            return Response(
                {"code": "invalid_fields", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("Bulk update failed", exc_info=True)
            return Response(
                self.error_class(
                    "Bulk update failed",
                    code="invalid_location_data",
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, *args, **kwargs):
        try:
            return self.bulk_delete(request)

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("Bulk delete failed", exc_info=True)
            return Response(
                self.error_class(
                    "Bulk delete failed",
                    code="invalid_location_data",
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# History API (Read-only list of historical versions)
class BaseHistoryListAPIView(BaseListAPIView):

    """
    ListAPIView for model history entries.
    Expects `history_queryset` and `history_serializer_class` defined in child.
    """

    # Disable filtering entirely for history
    filter_backends = []
    filterset_fields = []

    # We override get_queryset to use history_queryset, typically

    def get_queryset(self):
        # 🔒 Schema-generation safety (no runtime assumptions)
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        # `history_queryset` should be defined in child views
        return getattr(self, "history_queryset", self.queryset.none())

    def get(self, request, *args, **kwargs):
        # Use BaseListAPIView's get for pagination/filtering/caching
        return super().get(request, *args, **kwargs)

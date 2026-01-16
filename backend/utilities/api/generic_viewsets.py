import hashlib
import json
import logging
from typing import Any

from django.core.cache import cache
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from policyengine.components.actions import MODEL_ROLE_PERMISSIONS
from policyengine.components.permissions import get_action_based_permissions
from rest_framework import filters, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from utilities.api.generic_api_exceptions import GenericAPIError
from utilities.api.mixins import CacheMixin, SoftDeleteMixin
from utilities.api.mixins.serializer_resolution import SerializerByActionMixin
from utilities.api.rate_limits import CustomThrottle

logger = logging.getLogger(__name__)


class BaseViewSet(SerializerByActionMixin, SoftDeleteMixin, CacheMixin, ModelViewSet):

    """
    Generic reusable ViewSet:
    - Caching for list/retrieve
    - Explicit separation of serializer vs domain vs system errors
    - Throttling, filtering, pagination
    - Standard CRUD logging and cache invalidation
    """

    permission_classes = (IsAuthenticated,)
    throttle_classes = [CustomThrottle]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    cache_timeout = 172800

    # Override per app (e.g. InvalidLocationData)
    error_class = GenericAPIError

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def get_permissions(self):
        allowed_actions = MODEL_ROLE_PERMISSIONS.get(
            self.queryset.model.__name__.lower(), {}
        )
        return get_action_based_permissions(
            self.permission_classes,
            action_permissions=allowed_actions,
            view=self,
        )

    # ------------------------------------------------------------------
    # Queryset helpers
    # ------------------------------------------------------------------
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            return queryset
        return queryset

    def get_object(self):
        pk = self.kwargs.get("pk")
        return self.get_queryset().get(pk=pk)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            query_params = json.dumps(request.query_params.dict(), sort_keys=True)
            page_number = request.query_params.get("page", 1)
            model_name = self.queryset.model.__name__.lower()
            params_hash = hashlib.sha256(query_params.encode()).hexdigest()
            # cache_key = f"{model_name}_list_{request.user.id}_{page_number}_{hash(query_params)}"
            cache_key = f"{model_name}_list_{request.user.id}_{page_number}_{params_hash}"

            cached = self.get_cached_data(cache_key)
            if cached:
                return Response(cached)

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

            self.cache_data(cache_key, data, timeout=self.cache_timeout)
            return Response(data)

        except Exception:
            logger.error("List failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to list records",
                    code="invalid_location_data",
                    details={"operation": "list"},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            pk = kwargs.get("pk")
            model_name = self.queryset.model.__name__.lower()
            cache_key = f"{model_name}_detail_{pk}_{request.user.id}"

            cached = self.get_cached_data(cache_key)
            if cached:
                return Response(cached)

            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data

            self.cache_data(cache_key, data, timeout=self.cache_timeout)
            return Response(data)

        except self.queryset.model.DoesNotExist:
            return Response(
                {"detail": f"{self.queryset.model.__name__} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception:
            logger.error("Retrieve failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to retrieve record",
                    code="retrieve_error",
                    details={"operation": "retrieve", "pk": kwargs.get("pk")},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            response = super().create(request, *args, **kwargs)
            self._invalidate_cache("create")
            return response

        except DRFValidationError as e:
            return Response(
                {
                    "code": "invalid_fields",
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("Create failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to create record",
                    code="invalid_location_data",
                    details={"operation": "create"},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Update / Partial update
    # ------------------------------------------------------------------
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            response = super().update(request, *args, **kwargs)
            self._invalidate_cache("update")
            return response

        except DRFValidationError as e:
            return Response(
                {
                    "code": "invalid_fields",
                    "errors": e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("Update failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to update record",
                    code="invalid_location_data",
                    details={"operation": "update"},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def soft_delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            instance = self.get_object()
            instance.soft_delete(user=request.user)
            self._invalidate_cache("soft_delete")
            return Response(status=status.HTTP_204_NO_CONTENT)

        except self.error_class as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            logger.error("Soft delete failed", exc_info=True)
            return Response(
                self.error_class(
                    "Failed to delete record",
                    code="invalid_location_data",
                    details={"operation": "soft_delete"},
                ).to_dict(),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def paginate_queryset(self, queryset: QuerySet) -> Any:
        return super().paginate_queryset(queryset)

    def _invalidate_cache(self, operation: str) -> None:
        model_name = self.queryset.model.__name__.lower()
        cache.delete_pattern(f"{model_name}_list_*")
        cache.delete_pattern(f"{model_name}_detail_*")
        logger.info("Cache invalidated for %s after %s", model_name, operation)

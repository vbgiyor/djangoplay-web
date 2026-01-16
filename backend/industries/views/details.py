import logging

from apidocs.utils.base_schema import BaseSchema
from apidocs.utils.querysanitizer import add_sanitization_filter_to_logger
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from policyengine.components.permissions import get_action_based_permissions
from rest_framework import permissions, status
from rest_framework.generics import RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from utilities.api.rate_limits import CustomThrottle

from ..exceptions import InvalidIndustryData
from ..models import Industry
from ..serializers import IndustryReadSerializerV1

logger = logging.getLogger(__name__)
add_sanitization_filter_to_logger(logger)


@extend_schema(tags=["Industries"])
class IndustryDetailAPIView(RetrieveAPIView):

    """
    Detailed API view for retrieving a single Industry record.

    Features:
    - Uses IndustryDetailSerializer for nested children & metadata.
    - Caches responses based on user, pk, and last updated timestamp.
    - Stricter permissions via action-based permissions mapping.
    - Read-only endpoint (GET only).
    """

    queryset = Industry.objects.filter(deleted_at__isnull=True)
    serializer_class = IndustryReadSerializerV1
    permission_classes = (permissions.IsAuthenticated, permissions.DjangoModelPermissions)
    throttle_classes = [CustomThrottle]
    error_class = InvalidIndustryData
    cache_timeout = 604800  # 7 days for less frequently updated data

    def get_permissions(self):
        """
        Use action-based permissions, similar to CustomCountryDetailAPIView.
        """
        # You can customize this mapping as needed:
        allowed_actions = {
            'view_detailed_industry': ['industries.view_industry']
        }
        return get_action_based_permissions(
            self.permission_classes,
            action_permissions=allowed_actions,
            view=self
        )

    def get_queryset(self):
        """
        Optimize queryset with select_related / prefetch_related for related data.
        """
        return self.queryset.select_related(
            'created_by', 'updated_by'
        ).prefetch_related(
            'children', 'parent'
        )

    def _get_cache_key(self, pk: int, user_id: int, last_updated: str) -> str:
        """
        Build cache key including last updated fingerprint.
        """
        return f"industry_details_{pk}_{user_id}_{last_updated}"

    @BaseSchema.get_common_schema(
        summary="Retrieve Detailed Industry Information",
        description=(
        """
        * Retrieve detailed information for a specific industry by ID, including:
            - parent info
            - children list and counts
            - last_updated_timestamp from history
        """
        ),
        serializer_class=IndustryReadSerializerV1,
        operation_id='industries_detailed_retrieve',
        include_cache=True,
    )
    def get(self, request: Request, pk: int, *args, **kwargs) -> Response:
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated access attempt to {self.__class__.__name__} for pk={pk}")
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Validate pk
        try:
            pk = int(pk)
        except ValueError:
            logger.warning(f"Invalid ID '{pk}' in {self.__class__.__name__}")
            error = self.error_class(
                f"Invalid ID: {pk}",
                code="invalid_fields",
                details={"field": "pk", "value": pk},
            )
            return Response(error.to_dict(), status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get object from optimized queryset
            instance = self.get_object()

            # Determine last updated timestamp using history
            latest_history = instance.history.order_by('-history_date').first()
            last_updated = (
                latest_history.history_date.strftime('%Y%m%d%H%M%S')
                if latest_history else instance.updated_at.strftime('%Y%m%d%H%M%S')
            )

            # Check cache
            cache_key = self._get_cache_key(pk, request.user.id, last_updated)
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit: {cache_key}")
                return Response(cached_data)

            # Serialize
            serializer = self.get_serializer(instance)
            data = serializer.data

            # Cache response
            cache.set(cache_key, data, timeout=self.cache_timeout)
            logger.info(f"Cached detailed industry response: {cache_key}")

            return Response(data)

        except Industry.DoesNotExist:
            logger.warning(f"Industry not found for id: {pk}")
            error = self.error_class(
                f"Industry not found for id: {pk}",
                code="retrieve_error",
                details={"model": "Industry", "pk": pk},
            )
            return Response(error.to_dict(), status=status.HTTP_404_NOT_FOUND)
        except InvalidIndustryData as e:
            logger.error(f"InvalidIndustryData when fetching detailed industry: {e}", exc_info=True)
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching detailed industry: {e}", exc_info=True)
            error = self.error_class(
                f"Failed to fetch detailed industry: {str(e)}",
                code="retrieve_error",
                details={"operation": "fetch", "model": "Industry", "pk": pk},
            )
            return Response(error.to_dict(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

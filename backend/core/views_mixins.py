import json
import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django_redis import get_redis_connection
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


class BaseViewSetMixin:

    """
    Base mixin for ViewSets to provide common functionality like caching and logging.
    Assumes the ViewSet has a `model_name` attribute for cache keys (e.g., 'invoices', 'line_items').
    """

    model_name = None  # Must be set by the ViewSet (e.g., 'invoices', 'line_items')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.model_name:
            raise ValueError("ViewSet must define 'model_name' for caching.")
        self.logger = logging.getLogger(f"views.{self.model_name}")
        self.redis_client = get_redis_connection('default')

    def list(self, request, *args, **kwargs):
        """List objects with caching."""
        cache_key = f"{self.model_name}_list_{request.user.id}_{json.dumps(sorted(request.query_params.items()))}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            self.logger.debug(f"Cache hit for {self.model_name} list: {cache_key}")
            return Response(json.loads(cached_data))

        try:
            response = super().list(request, *args, **kwargs)
            self.redis_client.setex(cache_key, 3600, json.dumps(response.data))
            self.logger.info(f"Cached {self.model_name} list: {cache_key}")
            return response
        except Exception as e:
            self.logger.error(f"Error listing {self.model_name} for user {request.user}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to list {self.model_name}: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Create object and invalidate cache."""
        instance = serializer.save(created_by=self.request.user)
        self.redis_client.delete(f"{self.model_name}_list_{self.request.user.id}_*")
        self.logger.info(f"Invalidated cache for {self.model_name} after creation by user {self.request.user.id}")
        return instance

    def perform_update(self, serializer):
        """Update object and invalidate cache."""
        instance = serializer.save(updated_by=self.request.user)
        self.redis_client.delete(f"{self.model_name}_list_{self.request.user.id}_*")
        self.logger.info(f"Invalidated cache for {self.model_name} after update by user {self.request.user.id}")
        return instance

class BulkSoftDeleteMixin(PermissionRequiredMixin):

    """
    Mixin to handle bulk soft deletion and single object soft deletion.
    Assumes the model has a `soft_delete` method that accepts a `user` parameter.
    """

    def destroy(self, request, *args, **kwargs):
        """Soft delete a single object and invalidate cache."""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            self.redis_client.delete(f"{self.model_name}_list_{self.request.user.id}_*")
            self.logger.info(f"Soft deleted {self.model_name}: {instance}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            self.logger.error(f"Error soft deleting {self.model_name} for user {request.user}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to soft delete {self.model_name}: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        """Perform soft deletion for a single object."""
        try:
            instance.soft_delete(user=self.request.user)
        except Exception as e:
            raise ValidationError(
                detail=f"Failed to soft delete {self.model_name}: {str(e)}",
                code="soft_delete_error"
            )

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bulk_delete(self, request):
        """Bulk soft delete objects."""
        try:
            ids = request.data.get('ids', [])
            if not ids:
                return Response(
                    {'error': 'No IDs provided for bulk deletion.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = self.get_queryset().filter(id__in=ids, deleted_at__isnull=True)
            count = 0
            for instance in queryset:
                self.perform_destroy(instance)
                count += 1
            self.redis_client.delete(f"{self.model_name}_list_{self.request.user.id}_*")
            self.logger.info(f"Bulk soft deleted {count} {self.model_name} items by user {self.request.user.id}")
            return Response({'detail': f'Successfully soft deleted {count} items.'}, status=status.HTTP_200_OK)
        except Exception as e:
            self.logger.error(f"Error bulk soft deleting {self.model_name} for user {request.user}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to bulk soft delete {self.model_name}: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

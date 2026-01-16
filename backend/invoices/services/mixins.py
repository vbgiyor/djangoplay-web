import json
import logging
from typing import Any, Dict, Optional

from core.utils.redis_client import redis_client

from invoices.exceptions import InvoiceValidationError

logger = logging.getLogger(__name__)

class SoftDeleteMixin:

    """Mixin to handle soft delete and restore actions for Django models."""

    def perform_destroy(self, instance: Any, user: Optional[Any] = None) -> None:
        """Perform soft delete on the instance."""
        logger.debug(f"Soft deleting {instance.__class__.__name__}: {instance}, user: {user.id if user else 'None'}")
        try:
            instance.soft_delete(user=user)
            logger.info(f"Successfully soft deleted {instance.__class__.__name__}: {instance}")
        except Exception as e:
            logger.error(f"Error soft deleting {instance.__class__.__name__} {instance}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to soft delete {instance.__class__.__name__.lower()}: {str(e)}",
                code="soft_delete_error"
            )

    def perform_restore(self, instance: Any, user: Optional[Any] = None) -> None:
        """Perform restore on the instance."""
        logger.debug(f"Restoring {instance.__class__.__name__}: {instance}, user: {user.id if user else 'None'}")
        try:
            instance.restore(user=user)
            logger.info(f"Successfully restored {instance.__class__.__name__}: {instance}")
        except Exception as e:
            logger.error(f"Error restoring {instance.__class__.__name__} {instance}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to restore {instance.__class__.__name__.lower()}: {str(e)}",
                code="restore_error"
            )

class CacheMixin:

    """Mixin to handle Redis caching for viewsets."""

    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Retrieve data from Redis cache."""
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error fetching cache key {cache_key}: {str(e)}", exc_info=True)
        return None

    def cache_data(self, cache_key: str, data: Any, timeout: int = 3600) -> None:
        """Cache data in Redis with specified timeout."""
        try:
            redis_client.setex(cache_key, timeout, json.dumps(data))
            logger.debug(f"Cached data at: {cache_key}")
        except Exception as e:
            logger.error(f"Error caching data at {cache_key}: {str(e)}", exc_info=True)

    def invalidate_cache_pattern(self, pattern: str) -> None:
        """Invalidate cache keys matching the given pattern."""
        try:
            cursor = '0'
            while cursor != 0:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=1000)
                if keys:
                    redis_client.delete(*keys)
                    logger.debug(f"Invalidated cache keys matching: {pattern}")
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {str(e)}", exc_info=True)

import json
import logging
from typing import Any, Dict, Optional

from core.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

class CacheMixin:

    """Mixin to handle Redis caching for viewsets."""

    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Retrieve data from Redis cache."""
        if not self.request.user.is_authenticated:
            logger.debug("Skipping cache for unauthenticated user")
            return None
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error fetching cache key {cache_key}: {str(e)}", exc_info=True)
        return None

    def cache_data(self, cache_key: str, data: Any, timeout: int = 3600) -> None:
        """Cache data in Redis with specified timeout."""
        if not self.request.user.is_authenticated:
            logger.debug("Skipping cache for unauthenticated user")
            return
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

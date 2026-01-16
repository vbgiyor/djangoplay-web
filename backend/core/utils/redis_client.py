"""
Lazy proxy for the django_redis connection object.

This preserves the existing public symbol `redis_client` so existing imports
like `from core.utils.redis_client import redis_client` continue to work,
while deferring the real connection until the first runtime use (no DB/IO
at import time).
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Iterable, Optional

from django_redis import get_redis_connection
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class _RedisClientProxy:

    """
    A proxy object that lazily requests the real redis connection on first use.
    It tries to behave like the redis client returned by django_redis.get_redis_connection.
    """

    def __init__(self, alias: str = "default"):
        self._alias = alias
        self._real = None
        self._lock = threading.RLock()

    def _ensure_connected(self):
        # Double-checked locking to avoid races
        if self._real is None:
            with self._lock:
                if self._real is None:
                    try:
                        self._real = get_redis_connection(self._alias)
                        logger.info("Lazy Redis connection initialized via django_redis.")
                    except (RedisError, ConnectionInterrupted) as e:
                        logger.error("Failed to initialize Redis connection: %s - %s", type(e).__name__, str(e))
                        raise
                    except Exception:  # pragma: no cover - defensive
                        logger.exception("Unexpected error initializing Redis connection")
                        raise

    def __getattr__(self, item: str) -> Any:
        """
        Delegate attribute access to the real redis client, connecting if necessary.
        """
        self._ensure_connected()
        return getattr(self._real, item)

    def __repr__(self) -> str:
        if self._real is None:
            return f"<LazyRedisProxy(alias={self._alias}, connected=False)>"
        return repr(self._real)

    # Provide a few convenience helpers that operate even if not connected yet;
    # they will trigger connection when called.
    def get(self, *args, **kwargs):
        self._ensure_connected()
        return self._real.get(*args, **kwargs)

    def setex(self, *args, **kwargs):
        self._ensure_connected()
        return self._real.setex(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._ensure_connected()
        return self._real.delete(*args, **kwargs)

    def hkeys(self, *args, **kwargs):
        self._ensure_connected()
        return self._real.hkeys(*args, **kwargs)

    def hgetall(self, *args, **kwargs):
        self._ensure_connected()
        return self._real.hgetall(*args, **kwargs)

    # If you want direct access to the underlying connection (rare)
    @property
    def _connection(self):
        self._ensure_connected()
        return self._real


# Export the proxy instance under the old name so existing imports remain valid.
redis_client = _RedisClientProxy()

# Lightweight safe wrappers (optional)
def safe_get(key: str) -> Optional[bytes]:
    try:
        return redis_client.get(key)
    except Exception:
        logger.exception("safe_get failed for key: %s", key)
        return None

def safe_setex(key: str, seconds: int, value: Any) -> bool:
    try:
        redis_client.setex(key, seconds, value)
        return True
    except Exception:
        logger.exception("safe_setex failed for key: %s", key)
        return False

def safe_delete(*keys: Iterable[str]) -> int:
    try:
        return redis_client.delete(*keys)
    except Exception:
        logger.exception("safe_delete failed for keys: %s", keys)
        return 0


# import logging
# from django_redis import get_redis_connection
# from redis.exceptions import RedisError
# from django_redis.exceptions import ConnectionInterrupted

# logger = logging.getLogger(__name__)

# class RedisClient:
#     """
#     A class to provide a singleton Redis client instance using django_redis.

#     This ensures that a connection is established once and reused across the application.
#     It includes comprehensive error handling during connection and initialization.
#     Please note, through out the project we are using colons : instead of underscores _ for individual record keys
#     Page-based, search, and autocomplete keys use underscores _ while naming their cache keys
#     """
#     _client = None

#     @classmethod
#     def get_client(cls):
#         """
#         Retrieves the singleton Redis client instance.

#         If the client has not been initialized yet, it attempts to establish a
#         connection and handles various connection-related exceptions.

#         Returns:
#             redis.StrictRedis: The connected Redis client instance.

#         Raises:
#             Exception: If the Redis client cannot be initialized due to an error.
#         """
#         if cls._client is None:
#             try:
#                 # Use django_redis's get_redis_connection which handles the Django cache configuration
#                 cls._client = get_redis_connection('default')
#                 logger.info("Redis client initialized successfully via django_redis.")
#             except (RedisError, ConnectionInterrupted) as e:
#                 # Catch specific, actionable exceptions from Redis and django_redis
#                 logger.error(f"Failed to initialize Redis client: {type(e).__name__} - {str(e)}")
#                 raise
#             except Exception as e:
#                 # Catch any other unexpected exceptions during initialization, including CacheKeyError
#                 logger.error(f"Unexpected error initializing Redis client: {str(e)}")
#                 raise

#         return cls._client

# redis_client = RedisClient.get_client()

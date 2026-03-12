from .common import get_decrypted_value, env

# Decrypt and cast REDIS_PORT and REDIS_DB
REDIS_PORT = int(get_decrypted_value("REDIS_PORT", default="6379"))
REDIS_DB   = int(get_decrypted_value("REDIS_DB", default="1"))
REDIS_HOST = get_decrypted_value("REDIS_HOST", default="127.0.0.1")

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': env('REDIS_PASSWORD'),
            'SSL': env('REDIS_SSL', default=False),
            'CONNECTION_POOL_KWARGS': {'max_connections': 200},
            'PING_INTERVAL': 60,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}

LOCATION_CACHE_TIMEOUT = env('LOCATION_CACHE_TIMEOUT', default=3600)

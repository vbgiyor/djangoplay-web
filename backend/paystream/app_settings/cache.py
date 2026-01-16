from .common import decrypt_value, env, key_bytes

# Decrypt and cast REDIS_PORT and REDIS_DB
REDIS_PORT = int(decrypt_value(env('REDIS_PORT', default='6379'), key_bytes))
REDIS_DB = int(decrypt_value(env('REDIS_DB', default='1'), key_bytes))
REDIS_HOST = decrypt_value(env('REDIS_HOST', default='127.0.0.1'), key_bytes)

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

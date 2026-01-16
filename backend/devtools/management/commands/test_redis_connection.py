import logging

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test Redis connection and cache functionality'

    def handle(self, *args, **kwargs):
        try:
            redis_conn = get_redis_connection('default')
            # Access DB number from connection pool
            redis_db = redis_conn.connection_pool.connection_kwargs['db']
            logger.debug(
                f"Redis connection details: host={redis_conn.connection_pool.connection_kwargs['host']}, "
                f"port={redis_conn.connection_pool.connection_kwargs['port']}, "
                f"db={redis_db}"
            )

            # Test setting and getting a key
            redis_conn.set('test_key', 'test_value', ex=60)
            result = redis_conn.get('test_key')
            result = result.decode('utf-8') if result else None

            if result == 'test_value':
                logger.info(f"Redis connection successful: set and retrieved test_key on DB {redis_db}")
                self.stdout.write(self.style.SUCCESS(f"Redis connection successful on DB {redis_db}"))

                # Verify key in Redis
                keys = redis_conn.keys('test_key')
                logger.info(f"Keys found in DB {redis_db}: {keys}")
            else:
                logger.error("Redis connection failed: could not retrieve test_key")
                self.stdout.write(self.style.ERROR("Redis connection failed"))

            # Verify DB selection
            redis_conn.execute_command('SELECT', redis_db)
            logger.info(f"Confirmed Redis DB: {redis_db}")
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Redis connection error: {str(e)}"))

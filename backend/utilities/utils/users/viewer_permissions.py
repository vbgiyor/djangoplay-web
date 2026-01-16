import json
import logging
import zlib

from core.utils.redis_client import redis_client
from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def setup_viewer_group():
    """Create or update Viewer group with view permissions, caching with Redis."""
    cache_key = 'viewer_group_setup'

    # Check Redis cache
    cached_data = redis_client.get(cache_key)
    if cached_data:
        try:
            logger.debug(f"Cache hit for Viewer group setup: {cache_key}")
            return Group.objects.get(name='Viewer')
        except Group.DoesNotExist:
            logger.warning(f"Viewer group not found in DB but cached in Redis. Clearing cache: {cache_key}")
            redis_client.delete(cache_key)

    # Create or get Viewer group
    viewer_group, created = Group.objects.get_or_create(name='Viewer')

    # Cache permissions data
    permissions_data = []
    app_labels = ['entities', 'users', 'locations', 'industries', 'fincore', 'invoices']
    for app_label in app_labels:
        try:
            app_config = apps.get_app_config(app_label)
            for model in app_config.get_models():
                content_type = ContentType.objects.get_for_model(model)
                permission_codename = f"view_{model._meta.model_name}"
                permission, _ = Permission.objects.get_or_create(
                    content_type=content_type,
                    codename=permission_codename,
                    defaults={'name': f"Can view {model._meta.verbose_name}"}
                )
                viewer_group.permissions.add(permission)
                permissions_data.append({
                    'codename': permission_codename,
                    'content_type_id': content_type.id,
                    'name': permission.name
                })
                logger.debug(f"Added permission {permission_codename} to Viewer group")
        except Exception as e:
            logger.error(f"Error setting up Viewer group for app {app_label}: {str(e)}")

    # Store in Redis with compression
    try:
        redis_client.setex(
            cache_key,
            86400,  # Cache for 1 day
            zlib.compress(json.dumps({'group_name': 'Viewer', 'permissions': permissions_data}).encode())
        )
        logger.info(f"Cached Viewer group setup: {cache_key}")
    except Exception as e:
        logger.error(f"Failed to cache Viewer group setup: {str(e)}")

    logger.info("Viewer group setup completed")
    return viewer_group

import logging

from apidocs.models.apirequestlog import APIRequestLog
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import resolve
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=APIRequestLog)
def auto_set_is_public_api(sender, instance, **kwargs):
    if instance.pk:  # Only on creation
        return

    try:
        match = resolve(instance.path)
        view = match.func

        # DRF ViewSet or APIView
        perms = getattr(view, 'permission_classes', [])
        has_auth = any(issubclass(p, IsAuthenticated) for p in perms)

        instance.is_public_api = not has_auth
        logger.debug(f"Auto-set is_public_api={instance.is_public_api} for {instance.path}")
    except Exception as e:
        logger.warning(f"Failed to resolve path {instance.path}: {e}")
        instance.is_public_api = False

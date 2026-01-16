import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from utilities.utils.general.normalize_text import normalize_text

from entities.models.entity import Entity

# Logger for entities app
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Entity)
def pre_save_entity(sender, instance, **kwargs):
    """Handle pre-save operations for Entity, such as generating slug and normalizing fields."""
    logger.debug(f"Pre-save signal for Entity: {instance.name or 'New Entity'}")
    if not instance.slug:
        instance.slug = normalize_text(instance.name)
        logger.info(f"Generated slug for Entity: {instance.slug}")
    if instance.name:
        instance.name = normalize_text(instance.name)
    if instance.registration_number:
        instance.registration_number = normalize_text(instance.registration_number)
    if instance.entity_size:
        instance.entity_size = normalize_text(instance.entity_size)
    if instance.notes:
        instance.notes = normalize_text(instance.notes)

@receiver(post_save, sender=Entity)
def post_save_entity(sender, instance, created, **kwargs):
    """Handle post-save operations for Entity, such as creating entity mapping and logging."""
    with transaction.atomic():
        if created:
            logger.info(f"Entity created: {instance} (ID: {instance.pk})")
            # Ensure entity mapping is created
            mapping = instance.get_entity_mapping()
            logger.debug(f"Created FincoreEntityMapping for Entity: {instance}, Mapping: {mapping}")
        else:
            logger.info(f"Entity updated: {instance} (ID: {instance.pk})")
        # Invalidate cache for entity
        cache_key = f"entity_{instance.id}"
        cache.delete(cache_key)
        logger.debug(f"Invalidated cache for Entity: {cache_key}")

@receiver(post_delete, sender=Entity)
def post_delete_entity(sender, instance, **kwargs):
    """Handle post-delete operations for Entity, such as cache invalidation."""
    logger.info(f"Entity soft-deleted: {instance} (ID: {instance.pk})")
    cache_key = f"entity_{instance.id}"
    cache.delete(cache_key)
    logger.debug(f"Invalidated cache for Entity: {cache_key}")

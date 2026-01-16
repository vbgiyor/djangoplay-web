import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from fincore.models.address import Address
from fincore.models.contact import Contact
from fincore.models.entity_mapping import FincoreEntityMapping
from fincore.models.tax_profile import TaxProfile
from utilities.utils.general.normalize_text import normalize_text

# Logger for fincore app
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Address)
def pre_save_address(sender, instance, **kwargs):
    """Handle pre-save operations for Address, such as normalizing fields."""
    logger.debug(f"Pre-save signal for Address: {instance.street_address or 'New Address'}")
    if instance.street_address:
        instance.street_address = normalize_text(instance.street_address)
    if instance.postal_code:
        instance.postal_code = normalize_text(instance.postal_code)

@receiver(post_save, sender=Address)
def post_save_address(sender, instance, created, **kwargs):
    """Handle post-save operations for Address, such as cache updates and logging."""
    with transaction.atomic():
        if created:
            logger.info(f"Address created: {instance} (ID: {instance.pk})")
        else:
            logger.info(f"Address updated: {instance} (ID: {instance.pk})")
        # Update cache for related objects
        cache.set(f"city_{instance.city_id}", instance.city, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        cache.set(f"country_{instance.country_id}", instance.country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.region:
            cache.set(f"region_{instance.region_id}", instance.region, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.subregion:
            cache.set(f"subregion_{instance.subregion_id}", instance.subregion, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.entity_mapping:
            cache.set(f"entity_mapping_{instance.entity_mapping_id}", instance.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.debug(f"Updated cache for Address: {instance}")

@receiver(post_delete, sender=Address)
def post_delete_address(sender, instance, **kwargs):
    """Handle post-delete operations for Address, such as cache invalidation."""
    logger.info(f"Address soft-deleted: {instance} (ID: {instance.pk})")
    cache_keys = [
        f"city_{instance.city_id}",
        f"country_{instance.country_id}",
        f"region_{instance.region_id}" if instance.region else None,
        f"subregion_{instance.subregion_id}" if instance.subregion else None,
        f"entity_mapping_{instance.entity_mapping_id}" if instance.entity_mapping else None,
    ]
    for key in filter(None, cache_keys):
        cache.delete(key)
        logger.debug(f"Invalidated cache: {key}")

@receiver(pre_save, sender=Contact)
def pre_save_contact(sender, instance, **kwargs):
    """Handle pre-save operations for Contact, such as normalizing fields."""
    logger.debug(f"Pre-save signal for Contact: {instance.name or 'New Contact'}")
    if instance.name:
        instance.name = normalize_text(instance.name)
    if instance.email:
        instance.email = normalize_text(instance.email)
    if instance.phone_number:
        instance.phone_number = normalize_text(instance.phone_number)

@receiver(post_save, sender=Contact)
def post_save_contact(sender, instance, created, **kwargs):
    """Handle post-save operations for Contact, such as cache updates and logging."""
    with transaction.atomic():
        if created:
            logger.info(f"Contact created: {instance} (ID: {instance.pk})")
        else:
            logger.info(f"Contact updated: {instance} (ID: {instance.pk})")
        if instance.entity_mapping:
            cache.set(f"entity_mapping_{instance.entity_mapping_id}", instance.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.country:
            cache.set(f"country_{instance.country_id}", instance.country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.debug(f"Updated cache for Contact: {instance}")

@receiver(post_delete, sender=Contact)
def post_delete_contact(sender, instance, **kwargs):
    """Handle post-delete operations for Contact, such as cache invalidation."""
    logger.info(f"Contact soft-deleted: {instance} (ID: {instance.pk})")
    cache_keys = [
        f"entity_mapping_{instance.entity_mapping_id}" if instance.entity_mapping else None,
        f"country_{instance.country_id}" if instance.country else None,
    ]
    for key in filter(None, cache_keys):
        cache.delete(key)
        logger.debug(f"Invalidated cache: {key}")

@receiver(pre_save, sender=TaxProfile)
def pre_save_tax_profile(sender, instance, **kwargs):
    """Handle pre-save operations for TaxProfile, such as normalizing fields."""
    logger.debug(f"Pre-save signal for TaxProfile: {instance.tax_identifier or 'New TaxProfile'}")
    if instance.tax_identifier:
        instance.tax_identifier = normalize_text(instance.tax_identifier)
    if instance.tax_exemption_reason:
        instance.tax_exemption_reason = normalize_text(instance.tax_exemption_reason)

@receiver(post_save, sender=TaxProfile)
def post_save_tax_profile(sender, instance, created, **kwargs):
    """Handle post-save operations for TaxProfile, such as cache updates and logging."""
    with transaction.atomic():
        if created:
            logger.info(f"TaxProfile created: {instance} (ID: {instance.pk})")
        else:
            logger.info(f"TaxProfile updated: {instance} (ID: {instance.pk})")
        cache.set(f"country_{instance.country_id}", instance.country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.region:
            cache.set(f"region_{instance.region_id}", instance.region, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if instance.entity_mapping:
            cache.set(f"entity_mapping_{instance.entity_mapping_id}", instance.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.debug(f"Updated cache for TaxProfile: {instance}")

@receiver(post_delete, sender=TaxProfile)
def post_delete_tax_profile(sender, instance, **kwargs):
    """Handle post-delete operations for TaxProfile, such as cache invalidation."""
    logger.info(f"TaxProfile soft-deleted: {instance} (ID: {instance.pk})")
    cache_keys = [
        f"country_{instance.country_id}",
        f"region_{instance.region_id}" if instance.region else None,
        f"entity_mapping_{instance.entity_mapping_id}" if instance.entity_mapping else None,
    ]
    for key in filter(None, cache_keys):
        cache.delete(key)
        logger.debug(f"Invalidated cache: {key}")

@receiver(post_save, sender=FincoreEntityMapping)
def post_save_entity_mapping(sender, instance, created, **kwargs):
    """Handle post-save operations for FincoreEntityMapping, such as logging and cache updates."""
    if created:
        logger.info(f"FincoreEntityMapping created: {instance} (ID: {instance.pk})")
    else:
        logger.info(f"FincoreEntityMapping updated: {instance} (ID: {instance.pk})")
    cache.set(f"entity_mapping_{instance.id}", instance, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
    logger.debug(f"Updated cache for FincoreEntityMapping: {instance}")

@receiver(post_delete, sender=FincoreEntityMapping)
def post_delete_entity_mapping(sender, instance, **kwargs):
    """Handle post-delete operations for FincoreEntityMapping, such as cache invalidation."""
    logger.info(f"FincoreEntityMapping deleted: {instance} (ID: {instance.pk})")
    cache_key = f"entity_mapping_{instance.id}"
    cache.delete(cache_key)
    logger.debug(f"Invalidated cache: {cache_key}")

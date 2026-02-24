import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from locations.exceptions import InvalidLocationData
from locations.models.custom_city import CustomCity
from locations.models.custom_country import CustomCountry
from locations.models.custom_region import CustomRegion
from locations.models.custom_subregion import CustomSubRegion
from locations.models.global_region import GlobalRegion
from locations.models.location import Location
from locations.models.timezone import Timezone

logger = logging.getLogger('locations.signals')

def _cascade_soft_delete(model, queryset, parent_model_name, parent_instance, user=None):
    """Helper function to soft delete related objects."""
    logger.debug(f"Cascading soft delete for {model.__name__} related to {parent_model_name}: {parent_instance}")
    try:
        for instance in queryset:
            instance.soft_delete(user=user)
            logger.info(f"Soft deleted {model.__name__} {instance} due to {parent_model_name} {parent_instance} deletion")
    except Exception as e:
        logger.error(f"Error soft deleting {model.__name__} for {parent_model_name} {parent_instance}: {str(e)}", exc_info=True)
        raise InvalidLocationData(
            f"Failed to soft delete {model.__name__.lower()}s for {parent_model_name} {parent_instance}: {str(e)}",
            code="cascade_delete_error",
            details={"model": model.__name__, "parent_model": parent_model_name, "parent_id": getattr(parent_instance, 'id', None)}
        )

def _cascade_restore(model, queryset, parent_model_name, parent_instance, user=None):
    """Helper function to restore related objects."""
    logger.debug(f"Cascading restore for {model.__name__} related to {parent_model_name}: {parent_instance}")
    try:
        for instance in queryset:
            instance.restore(user=user)
            logger.info(f"Restored {model.__name__} {instance} due to {parent_model_name} {parent_instance} restoration")
    except Exception as e:
        logger.error(f"Error restoring {model.__name__} for {parent_model_name} {parent_instance}: {str(e)}", exc_info=True)
        raise InvalidLocationData(
            f"Failed to restore {model.__name__.lower()}s for {parent_model_name} {parent_instance}: {str(e)}",
            code="cascade_restore_error",
            details={"model": model.__name__, "parent_model": parent_model_name, "parent_id": getattr(parent_instance, 'id', None)}
        )

@receiver(pre_delete, sender=GlobalRegion)
def cascade_global_region_delete(sender, instance, **kwargs):
    """Soft delete countries associated with a global region on deletion."""
    logger.debug(f"Handling pre_delete for GlobalRegion: {instance.name} (ID: {instance.id})")
    queryset = CustomCountry.objects.filter(
        global_regions=instance, deleted_at__isnull=True
    ).select_related('created_by', 'updated_by')
    _cascade_soft_delete(CustomCountry, queryset, "GlobalRegion", instance)

@receiver(pre_delete, sender=CustomCountry)
def cascade_country_delete(sender, instance, **kwargs):
    """Soft delete regions associated with a country on deletion."""
    logger.debug(f"Handling pre_delete for CustomCountry: {instance.name} (ID: {instance.id})")
    queryset = CustomRegion.objects.filter(
        country=instance, deleted_at__isnull=True
    ).select_related('country', 'created_by', 'updated_by')
    _cascade_soft_delete(CustomRegion, queryset, "CustomCountry", instance)

@receiver(pre_delete, sender=CustomRegion)
def cascade_region_delete(sender, instance, **kwargs):
    """Soft delete subregions and cities associated with a region on deletion."""
    logger.debug(f"Handling pre_delete for CustomRegion: {instance.name} (ID: {instance.id})")
    subregion_queryset = CustomSubRegion.objects.filter(
        subregion__region=instance, deleted_at__isnull=True
    ).select_related('region', 'created_by', 'updated_by')
    city_queryset = CustomCity.objects.filter(
        subregion__region=instance, deleted_at__isnull=True
    ).select_related('country', 'region', 'subregion', 'timezone', 'created_by', 'updated_by')
    _cascade_soft_delete(CustomSubRegion, subregion_queryset, "CustomRegion", instance)
    _cascade_soft_delete(CustomCity, city_queryset, "CustomRegion", instance)

@receiver(pre_delete, sender=CustomSubRegion)
def cascade_subregion_delete(sender, instance, **kwargs):
    """Soft delete cities associated with a subregion on deletion."""
    logger.debug(f"Handling pre_delete for CustomSubRegion: {instance.name} (ID: {instance.id})")
    queryset = CustomCity.objects.filter(
        subsubregion__region=instance, deleted_at__isnull=True
    ).select_related('country', 'region', 'subregion', 'timezone', 'created_by', 'updated_by')
    _cascade_soft_delete(CustomCity, queryset, "CustomSubRegion", instance)

@receiver(pre_delete, sender=CustomCity)
def cascade_city_delete(sender, instance, **kwargs):
    """Soft delete locations associated with a city on deletion."""
    logger.debug(f"Handling pre_delete for CustomCity: {instance.name} (ID: {instance.id})")
    queryset = Location.objects.filter(
        city=instance, deleted_at__isnull=True
    ).select_related('city', 'created_by', 'updated_by')
    _cascade_soft_delete(Location, queryset, "CustomCity", instance)

@receiver(pre_delete, sender=Timezone)
def cascade_timezone_delete(sender, instance, **kwargs):
    """Set timezone to null in cities associated with a timezone on deletion."""
    logger.debug(f"Handling pre_delete for Timezone: {instance.display_name} (ID: {instance.timezone_id})")
    try:
        cities = CustomCity.objects.filter(
            timezone=instance, deleted_at__isnull=True
        ).select_related('country', 'region', 'subregion', 'timezone', 'created_by', 'updated_by')
        for city in cities:
            city.timezone = None
            city.save(user=None)
            logger.info(f"Set timezone to null for CustomCity {city.name} (ID: {city.id}) due to Timezone {instance.display_name} deletion")
    except Exception as e:
        logger.error(f"Error in cascade_timezone_delete for Timezone {instance.display_name}: {str(e)}", exc_info=True)
        raise InvalidLocationData(
            f"Failed to handle timezone deletion for Timezone {instance.display_name}: {str(e)}",
            code="cascade_delete_error",
            details={"model": "Timezone", "id": instance.timezone_id}
        )

@receiver(post_save, sender=GlobalRegion)
def handle_global_region_restore(sender, instance, **kwargs):
    """Restore countries when a global region is restored."""
    if instance.deleted_at is None:
        queryset = CustomCountry.objects.filter(
            global_regions=instance, deleted_at__isnull=False
        ).select_related('created_by', 'updated_by')
        _cascade_restore(CustomCountry, queryset, "GlobalRegion", instance)

@receiver(post_save, sender=CustomCountry)
def handle_country_restore(sender, instance, **kwargs):
    """Restore regions when a country is restored."""
    if instance.deleted_at is None:
        queryset = CustomRegion.objects.filter(
            country=instance, deleted_at__isnull=False
        ).select_related('country', 'created_by', 'updated_by')
        _cascade_restore(CustomRegion, queryset, "CustomCountry", instance)

@receiver(post_save, sender=CustomRegion)
def handle_region_restore(sender, instance, created, **kwargs):
    if created:
        return

    if instance.deleted_at is None:

        subregion_queryset = CustomSubRegion.objects.filter(
            region=instance,
            deleted_at__isnull=False
        ).select_related('region')

        city_queryset = CustomCity.objects.filter(
            subregion__region=instance,
            deleted_at__isnull=False
        ).select_related(
            'subregion',
            'subregion__region',
            'subregion__region__country',
            'timezone'
        )

        _cascade_restore(CustomSubRegion, subregion_queryset, "CustomRegion", instance)
        _cascade_restore(CustomCity, city_queryset, "CustomRegion", instance)

@receiver(post_save, sender=CustomSubRegion)
def handle_subregion_restore(sender, instance, **kwargs):
    """Restore cities when a subregion is restored."""
    if instance.deleted_at is None:
        queryset = CustomCity.objects.filter(
            subsubregion__region=instance, deleted_at__isnull=False
        ).select_related('country', 'region', 'subregion', 'timezone', 'created_by', 'updated_by')
        _cascade_restore(CustomCity, queryset, "CustomSubRegion", instance)

@receiver(post_save, sender=CustomCity)
def handle_city_restore(sender, instance, **kwargs):
    """Restore locations when a city is restored."""
    if instance.deleted_at is None:
        queryset = Location.objects.filter(
            city=instance, deleted_at__isnull=False
        ).select_related('city', 'created_by', 'updated_by')
        _cascade_restore(Location, queryset, "CustomCity", instance)

@receiver(post_save, sender=Timezone)
def handle_timezone_restore(sender, instance, **kwargs):
    """Log restoration of a timezone (no cascade needed)."""
    if instance.deleted_at is None:
        logger.info(f"Timezone {instance.display_name} (ID: {instance.timezone_id}) restored")

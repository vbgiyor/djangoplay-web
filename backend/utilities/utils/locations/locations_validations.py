import logging
import re

from django.apps import apps
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_country_code(value):
    """
    Validate that the country code is exactly 2 uppercase letters.
    """
    logger.debug(f"Validating country code: {value}")
    if value and not re.match(r'^[A-Z]{2}$', value):
        logger.error(f"Invalid country code: {value}")
        raise ValidationError('Country code must be exactly 2 uppercase letters.')
    return value

def validate_unique_city_name(name, country, region=None, subregion=None, instance=None):
    """
    Validate that a city name is unique within a country, region, and subregion.
    """
    logger.debug(f"Validating city name: {name} in country: {country}")
    queryset = apps.get_model('locations', 'CustomCity').objects.filter(
        name__iexact=name, country=country, deleted_at__isnull=True
    )
    if region:
        queryset = queryset.filter(region=region)
    if subregion:
        queryset = queryset.filter(subregion=subregion)
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        logger.error(f"City with name {name} already exists in country {country}")
        raise ValidationError('A city with this name already exists in the specified country, region, and subregion.')
    return name

def validate_location_hierarchy(country_id=None, region_id=None, subregion_id=None, city_id=None, global_region_id=None):
    """
    Validate the location hierarchy to ensure referential integrity.
    """
    logger.info(f"Validating location hierarchy: country_id={country_id}, region_id={region_id}, subregion_id={subregion_id}, city_id={city_id}, global_region_id={global_region_id}")
    try:
        CustomCity = apps.get_model('locations', 'CustomCity')
        CustomSubRegion = apps.get_model('locations', 'CustomSubRegion')
        CustomRegion = apps.get_model('locations', 'CustomRegion')
        CustomCountry = apps.get_model('locations', 'CustomCountry')
        GlobalRegion = apps.get_model('locations', 'GlobalRegion')

        if city_id:
            city = CustomCity.objects.get(id=city_id, deleted_at__isnull=True)
            if subregion_id and city.subregion_id != subregion_id:
                logger.error(f"City {city} does not belong to subregion ID {subregion_id}")
                raise ValidationError("City does not belong to the specified subregion.")
            if region_id and city.region_id != region_id:
                logger.error(f"City {city} does not belong to region ID {region_id}")
                raise ValidationError("City does not belong to the specified region.")
            if country_id and city.country_id != country_id:
                logger.error(f"City {city} does not belong to country ID {country_id}")
                raise ValidationError("City does not belong to the specified country.")
            subregion_id = city.subregion_id
            region_id = city.region_id
            country_id = city.country_id

        if subregion_id:
            subregion = CustomSubRegion.objects.get(id=subregion_id, deleted_at__isnull=True)
            if region_id and subregion.region_id != region_id:
                logger.error(f"Subregion {subregion} does not belong to region ID {region_id}")
                raise ValidationError("Subregion does not belong to the specified region.")
            region_id = subregion.region_id

        if region_id:
            region = CustomRegion.objects.get(id=region_id, deleted_at__isnull=True)
            if country_id and region.country_id != country_id:
                logger.error(f"Region {region} does not belong to country ID {country_id}")
                raise ValidationError("Region does not belong to the specified country.")
            country_id = region.country_id

        if country_id:
            CustomCountry.objects.get(id=country_id, deleted_at__isnull=True)

        if global_region_id:
            GlobalRegion.objects.get(id=global_region_id, deleted_at__isnull=True)

        logger.info("Location hierarchy validated successfully")
    except (CustomCity.DoesNotExist, CustomSubRegion.DoesNotExist, CustomRegion.DoesNotExist, CustomCountry.DoesNotExist, GlobalRegion.DoesNotExist) as e:
        logger.error(f"Error validating location hierarchy: {e}", exc_info=True)
        raise ValidationError(f"Invalid location reference: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in location hierarchy validation: {e}", exc_info=True)
        raise ValidationError(f"Unexpected error: {str(e)}")

import json
import logging
import zlib

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from core.utils.redis_client import redis_client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.postal_code_validations import validate_postal_code

from ..exceptions import InvalidLocationData
from .custom_city import CustomCity
from .custom_country import CustomCountry
from .custom_region import CustomRegion
from .custom_subregion import CustomSubRegion
from .timezone import Timezone

logger = logging.getLogger(__name__)

class Location(TimeStampedModel, AuditFieldsModel):

    """Location model for granular areas within a city and postal code validation."""

    city = models.ForeignKey(CustomCity, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=20, blank=True, null=True, help_text="Numeric administrative code for level 4 (e.g., '1234' for a locality)")
    postal_code = models.CharField(max_length=20, blank=True, null=True, help_text='Postal code (e.g., Indian PIN code for India)')
    street_address = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude of the location (optional)")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude of the location (optional)")
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of the location data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        ordering = ['city__name']
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        constraints = [
            models.UniqueConstraint(
                fields=['city', 'postal_code'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_location_city_postal_code'
            ),
            models.CheckConstraint(
                check=models.Q(latitude__gte=-90.0) & models.Q(latitude__lte=90.0),
                name='location_valid_latitude'
            ),
            models.CheckConstraint(
                check=models.Q(longitude__gte=-180.0) & models.Q(longitude__lte=180.0),
                name='location_valid_longitude'
            ),
        ]
        indexes = [
            models.Index(fields=['city', 'postal_code']),
            models.Index(fields=['latitude', 'longitude']),
            GinIndex(fields=['postal_code'], name='location_postal_code_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['street_address'], name='loc_street_address_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['location_source'], name='location_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        """String representation of location."""
        region_or_country = self.city.subregion.region.name if self.city.subregion.region else self.city.subregion.region.country.name
        postal_code = f", {self.postal_code}" if self.postal_code else ""
        return f"{self.city.name}{postal_code}, {region_or_country}"

    def clean(self):
        """Validate location data, including postal code."""
        logger.debug(f"Validating Location: city={self.city}, postal_code={self.postal_code}")
        if not self.city:
            raise ValidationError("City is required for a location.")
        if self.postal_code and self.city and self.city.subregion and self.city.subregion.region and self.city.subregion.region.country and self.city.subregion.region.country.country_code:
            try:
                validate_postal_code(self.postal_code, self.city.subregion.region.country.country_code)
            except ValidationError as e:
                logger.error(f"Postal code validation failed: {str(e)}")
                raise
        if self.code and not self.code.isascii():
            raise ValidationError(f"Admin4 code must be ASCII, got {self.code}")
        if self.code and len(self.code) > 20:
            raise ValidationError(f"Admin4 code must be 20 characters or less, got {self.code}")
        if not self.postal_code and Location.objects.filter(city=self.city, postal_code__isnull=True).exclude(pk=self.pk).exists():
            raise ValidationError("A location with this city and no postal code already exists.")
        if self.street_address:
            self.street_address = normalize_text(self.street_address)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save location with normalized fields."""
        logger.debug(f"Saving Location: city={self.city}, postal_code={self.postal_code}, user={user}")
        if not skip_validation:
            self.clean()
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        try:
            super().save(*args, **kwargs)
            logger.info(f"Successfully saved Location: city={self.city} (ID: {self.pk})")
        except Exception as e:
            logger.error(
                f"Failed to save Location: city={self.city}, postal_code={self.postal_code}, error={str(e)}",
                exc_info=True
            )
            raise ValidationError(f"Failed to save location: {str(e)}")
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        logger.info(f"Soft deleting Location: city={self.city}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive location.",
                code="inactive_location",
                details={"location_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted Location: city={self.city}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete Location: city={self.city}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete location: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        logger.info(f"Restoring Location: city={self.city}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active location.",
                code="already_active_location",
                details={"location_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored Location: city={self.city}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore Location: city={self.city}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore location: {str(e)}")

    def add_or_get_location(
        cls,
        city_name: str,
        region_name: str | None,
        country_name: str,
        subregion_name: str | None = None,
        postal_code: str | None = None,
        geoname_id: int | None = None,
        user=None,
        timezone_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        feature_code: str | None = None,
        admin3_code: str | None = None,
        admin4_code: str | None = None,
        location_source: str | None = None,
    ):
        """Add or get a location with caching, validation, and admin4_code handling."""
        logger.debug(f"Adding or getting location: city={city_name}, country={country_name}, feature_code={feature_code}, admin3_code={admin3_code}, admin4_code={admin4_code}, user={user}, location_source={location_source}")
        User = get_user_model()
        if user and not isinstance(user, User):
            logger.warning(f"Invalid user provided: {user}, setting to None")
            user = None
        # Normalize input parameters
        city_name = normalize_text(city_name.strip())
        country_name = normalize_text(country_name.strip())
        region_name = normalize_text(region_name.strip()) if region_name else None
        subregion_name = normalize_text(subregion_name.strip()) if subregion_name else None
        postal_code = postal_code.strip().upper() if postal_code else None
        timezone_id = timezone_id.strip() if timezone_id else None
        feature_code = feature_code.strip().upper() if feature_code else None
        admin3_code = admin3_code.strip() if admin3_code else None
        admin4_code = admin4_code.strip() if admin4_code else None
        location_source = normalize_text(location_source.strip()) if location_source else None
        # Validate numeric codes
        if admin3_code and not admin3_code.isdigit():
            raise InvalidLocationData(f"Admin3 code must be numeric, got {admin3_code}")
        if admin4_code and not admin4_code.isdigit():
            raise InvalidLocationData(f"Admin4 code must be numeric, got {admin4_code}")

        with transaction.atomic():
            redis = redis_client.get_client()
            cache_timeout = getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600)
            country_cache_key = f"country:{country_name.lower()}"
            region_cache_key = f"region:{region_name.lower()}:{country_name.lower()}" if region_name else None
            subregion_cache_key = f"subregion:{subregion_name.lower()}:{region_name.lower()}" if subregion_name else None
            city_cache_key = f"city:{city_name.lower()}:{country_name.lower()}:{region_name.lower() if region_name else 'none'}:{subregion_name.lower() if subregion_name else 'none'}"
            location_cache_key = f"location:{city_name.lower()}:{postal_code.lower() if postal_code else 'none'}"

            # Get or create country
            try:
                cached_country = redis.hget('countries', country_cache_key)
                country = CustomCountry(**json.loads(zlib.decompress(cached_country).decode())) if cached_country else None
            except Exception as e:
                logger.warning(f"Cache get failed for {country_cache_key}: {str(e)}")
                country = None
            if not country:
                country, _ = CustomCountry.objects.get_or_create(
                    name__iexact=country_name,
                    defaults={'name': country_name, 'geoname_id': geoname_id, 'created_by': user, 'updated_by': user, 'location_source': location_source}
                )
                try:
                    country_data = {
                        'id': country.id,
                        'name': country.name,
                        'country_code': country.country_code,
                        'location_source': country.location_source
                    }
                    redis.hset('countries', country_cache_key, zlib.compress(json.dumps(country_data).encode()))
                    redis.expire('countries', cache_timeout)
                except Exception as e:
                    logger.warning(f"Cache set failed for {country_cache_key}: {str(e)}")

            # Validate postal code early
            if postal_code and country.country_code:
                try:
                    validate_postal_code(postal_code, country.country_code)
                except ValidationError as e:
                    logger.error(f"Postal code validation failed: {str(e)}")
                    raise InvalidLocationData(f"Invalid postal code for {country.name}: {str(e)}")

            # Get or create region
            region = None
            if region_name:
                try:
                    cached_region = redis.hget('regions', region_cache_key)
                    region = CustomRegion(**json.loads(zlib.decompress(cached_region).decode())) if cached_region else None
                except Exception as e:
                    logger.warning(f"Cache get failed for {region_cache_key}: {str(e)}")
                    region = None
                if not region:
                    region, _ = CustomRegion.objects.get_or_create(
                        name__iexact=region_name,
                        country=country,
                        defaults={'name': region_name, 'geoname_id': geoname_id, 'created_by': user, 'updated_by': user, 'location_source': location_source}
                    )
                    try:
                        region_data = {
                            'id': region.id,
                            'name': region.name,
                            'country_id': region.country_id,
                            'country_name': country.name,
                            'location_source': region.location_source
                        }
                        redis.hset('regions', region_cache_key, zlib.compress(json.dumps(region_data).encode()))
                        redis.expire('regions', cache_timeout)
                    except Exception as e:
                        logger.warning(f"Cache set failed for {region_cache_key}: {str(e)}")

            # Get or create subregion
            subregion = None
            if subregion_name:
                if not region:
                    logger.error(f"Cannot create subregion without a region for {subregion_name}")
                    raise InvalidLocationData("Cannot create subregion without a region.")
                try:
                    cached_subregion = redis.hget('subregions', subregion_cache_key)
                    subregion = CustomSubRegion(**json.loads(zlib.decompress(cached_subregion).decode())) if cached_subregion else None
                except Exception as e:
                    logger.warning(f"Cache get failed for {subregion_cache_key}: {str(e)}")
                    subregion = None
                if not subregion:
                    subregion, _ = CustomSubRegion.objects.get_or_create(
                        name__iexact=subregion_name,
                        region=region,
                        defaults={'name': subregion_name, 'geoname_id': geoname_id, 'created_by': user, 'updated_by': user, 'location_source': location_source}
                    )
                    try:
                        subregion_data = {
                            'id': subregion.id,
                            'name': subregion.name,
                            'region_id': subregion.region_id,
                            'region_name': region.name,
                            'location_source': subregion.location_source
                        }
                        redis.hset('subregions', subregion_cache_key, zlib.compress(json.dumps(subregion_data).encode()))
                        redis.expire('subregions', cache_timeout)
                    except Exception as e:
                        logger.warning(f"Cache set failed for {subregion_cache_key}: {str(e)}")

            # Get or create timezone
            timezone = None
            if timezone_id:
                try:
                    timezone = Timezone.objects.get(timezone_id=timezone_id)
                except Timezone.DoesNotExist:
                    logger.warning(f"Timezone ID {timezone_id} not found, proceeding without timezone")
                    timezone = None

            # Get or create city
            try:
                cached_city = redis.hget('cities', city_cache_key)
                city = CustomCity(**json.loads(zlib.decompress(cached_city).decode())) if cached_city else None
            except Exception as e:
                logger.warning(f"Cache get failed for {city_cache_key}: {str(e)}")
                city = None
            if not city:
                city, _ = CustomCity.objects.get_or_create(
                    name__iexact=city_name,
                    subregion=subregion,
                    defaults={
                        'name': city_name,
                        'geoname_id': geoname_id,
                        'created_by': user,
                        'updated_by': user,
                        'timezone': timezone,
                        'latitude': latitude,
                        'longitude': longitude,
                        'code': admin3_code,
                        'location_source': location_source
                    }
                )
                try:
                    city_data = {
                        'id': city.id,
                        'name': city.name,
                        'subregion_id': city.subregion_id,
                        'subregion_name': subregion.name if subregion else None,
                        'location_source': city.location_source
                    }
                    redis.hset('cities', city_cache_key, zlib.compress(json.dumps(city_data).encode()))
                    redis.expire('cities', cache_timeout)
                except Exception as e:
                    logger.warning(f"Cache set failed for {city_cache_key}: {str(e)}")

            # Get or create location
            try:
                cached_location = redis.hget('locations', location_cache_key)
                location = Location(**json.loads(zlib.decompress(cached_location).decode())) if cached_location else None
            except Exception as e:
                logger.warning(f"Cache get failed for {location_cache_key}: {str(e)}")
                location = None
            if not location:
                location, _ = cls.objects.get_or_create(
                    city=city,
                    postal_code=postal_code,
                    defaults={
                        'created_by': user,
                        'updated_by': user,
                        'latitude': latitude,
                        'longitude': longitude,
                        'code': admin4_code,
                        'street_address': None,
                        'location_source': location_source
                    }
                )
                try:
                    location_data = {
                        'id': location.id,
                        'city_id': location.city_id,
                        'city_name': city.name,
                        'postal_code': location.postal_code,
                        'location_source': location.location_source
                    }
                    redis.hset('locations', location_cache_key, zlib.compress(json.dumps(location_data).encode()))
                    redis.expire('locations', cache_timeout)
                except Exception as e:
                    logger.warning(f"Cache set failed for {location_cache_key}: {str(e)}")

            logger.info(f"Successfully added or retrieved location: city={city_name}, country={country_name} (ID: {location.pk})")
            return location

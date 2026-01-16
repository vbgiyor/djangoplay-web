import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from .custom_subregion import CustomSubRegion

logger = logging.getLogger(__name__)

class CustomCity(TimeStampedModel, AuditFieldsModel):

    """City model with audit fields and optional geographic coordinates."""

    name = models.CharField(max_length=200, help_text="Name of the city")
    asciiname = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(max_length=200, blank=True)
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    code = models.CharField(max_length=20,blank=True, null=True, help_text="Numeric administrative code for level 3 (e.g., '4285' for Hatkanangale)" )
    subregion = models.ForeignKey(CustomSubRegion, on_delete=models.CASCADE, related_name='cities')
    latitude = models.FloatField(null=True, blank=True, help_text="Latitude of the city's central point (optional)")
    longitude = models.FloatField(null=True, blank=True, help_text="Longitude of the city's central point (optional)")
    # timezone = models.ForeignKey('Timezone', on_delete=models.SET_NULL, related_name='cities', null=True, blank=True, help_text='IANA Time Zone ID from Timezone model')
    timezone = models.ForeignKey('locations.Timezone', on_delete=models.SET_NULL, null=True, blank=True, to_field='timezone_id', db_column='timezone_id', related_name='cities')
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of the city data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        verbose_name = "City"
        verbose_name_plural = "Cities"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'subregion'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_city_name_subregion'
            ),
            models.CheckConstraint(
                check=models.Q(latitude__gte=-90.0) & models.Q(latitude__lte=90.0),
                name='valid_latitude'
            ),
            models.CheckConstraint(
                check=models.Q(longitude__gte=-180.0) & models.Q(longitude__lte=180.0),
                name='valid_longitude'
            ),
        ]
        indexes = [
            models.Index(fields=['geoname_id']),
            models.Index(fields=['name', 'subregion']),
            models.Index(fields=['latitude', 'longitude']),
            GinIndex(fields=['name'], name='custom_city_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['asciiname'], name='custom_city_asciiname_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['location_source'], name='custom_city_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
            ]
        unique_together = ['name', 'subregion']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate city data."""
        if not self.name:
            raise ValidationError("City name is required.")
        if not self.subregion:
            raise ValidationError("Subregion is required for a city.")
        if self.code and not self.code.isascii():
            raise ValidationError(f"Admin3 code must be ASCII, got {self.code}")
        if self.code and len(self.code) > 20:
            raise ValidationError(f"Admin3 code must be 20 characters or less, got {self.code}")
        self.name = normalize_text(self.name)
        if self.asciiname:
            self.asciiname = normalize_text(self.asciiname)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save city with normalized fields."""
        logger.debug(f"Saving CustomCity: name={self.name}, user={user}, pk={self.pk}")
        if not skip_validation:
            self.clean()
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        if not self.slug:
            self.slug = slugify(self.name)
        try:
            super().save(*args, **kwargs)
            logger.info(f"Successfully saved CustomCity: {self.name} (ID: {self.pk})")
        except Exception as e:
            logger.error(
                f"Failed to save CustomCity: {self.name}, error={str(e)}, "
                f"fields={{name={self.name}, subregion={self.subregion_id}, code={self.code}, latitude={self.latitude}, longitude={self.longitude}, location_source={self.location_source}}}",
                exc_info=True
            )
            raise ValidationError(f"Failed to save city: {str(e)}")
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete city."""
        logger.info(f"Soft deleting CustomCity: {self.name}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive city.",
                code="inactive_city",
                details={"city_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted CustomCity: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete CustomCity: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete city: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted city."""
        logger.info(f"Restoring CustomCity: {self.name}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active city.",
                code="already_active_city",
                details={"city_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored CustomCity: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore CustomCity: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore city: {str(e)}")

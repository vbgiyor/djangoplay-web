import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model

# from .custom_country import CustomCountry
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

logger = logging.getLogger(__name__)

class CustomRegion(TimeStampedModel, AuditFieldsModel):

    """Region model with audit fields (e.g., state in India)."""

    name = models.CharField(max_length=200, help_text="Name of the region (e.g., 'Kerala' for admin1_code '13')")
    asciiname = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Administrative Code", help_text="Numeric administrative code for level 1 (e.g., '13' for Kerala)")
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    slug = models.SlugField(max_length=200, blank=True)
    # country = models.ForeignKey(CustomCountry, on_delete=models.CASCADE, related_name='regions')
    country = models.ForeignKey('locations.CustomCountry', on_delete=models.CASCADE, related_name='regions')
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of country's region data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        verbose_name = "Region/State"
        verbose_name_plural = "Regions/States"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'country'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_region_name_country'
            ),
        ]
        indexes = [
            models.Index(fields=['geoname_id']),
            models.Index(fields=['code']),
            models.Index(fields=['name', 'country', 'slug', 'geoname_id']),
            GinIndex(fields=['name'], name='region_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['asciiname'], name='region_asciiname_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['location_source'], name='region_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
        ]
        unique_together = ['name', 'country']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate region data."""
        if not self.name:
            raise ValidationError("Region name is required.")
        if not self.country:
            raise ValidationError("Country is required for a region.")
        if self.code and not self.code.isascii():
            raise ValidationError(f"Admin1 code must be ASCII, got {self.code}")
        if self.code and len(self.code) > 20:
            raise ValidationError(f"Admin1 code must be 20 characters or less, got {self.code}")
        self.name = normalize_text(self.name)
        if self.asciiname:
            self.asciiname = normalize_text(self.asciiname)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save region with normalized fields."""
        logger.debug(f"Saving CustomRegion: {self.name}, user={user}")
        if not skip_validation:
            self.clean()
        User = get_user_model()
        is_new = self.pk is None
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        if not self.slug:
            self.slug = slugify(self.name)
        try:
            super().save(*args, **kwargs)
            # Manually create initial history for old records
            if is_new:
                self.history.create(
                    history_type='+',
                    history_date=self.created_at,
                    **{f.name: getattr(self, f.name) for f in self._meta.fields}
                )

            logger.info(f"Successfully saved CustomRegion: {self.name} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save CustomRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to save region: {str(e)}")
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete region."""
        logger.info(f"Soft deleting CustomRegion: {self.name}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive region.",
                code="inactive_region",
                details={"region_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted CustomRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete CustomRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete region: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted region."""
        logger.info(f"Restoring CustomRegion: {self.name}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active region.",
                code="already_active_region",
                details={"region_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored CustomRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore CustomRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore region: {str(e)}")

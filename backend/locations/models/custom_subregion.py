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

from .custom_region import CustomRegion

logger = logging.getLogger(__name__)

class CustomSubRegion(TimeStampedModel, AuditFieldsModel):

    """Subregion model with audit fields (e.g., district in India)."""

    name = models.CharField(max_length=200, help_text="Name of the subregion (e.g., 'Kolhapur' for admin2_code '594')")
    asciiname = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True, help_text="Numeric administrative code for level 2 (e.g., '594' for Kolhapur)")
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    slug = models.SlugField(max_length=200, blank=True)
    region = models.ForeignKey(CustomRegion, on_delete=models.CASCADE, related_name='subregions')
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of country's subregion data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        verbose_name = "Subregion/District"
        verbose_name_plural = "Subregions/Districts"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'region'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_subregion_name_region'
            ),
        ]
        indexes = [
            models.Index(fields=['geoname_id']),
            models.Index(fields=['code']),
            models.Index(fields=['name', 'region', 'slug', 'geoname_id']),
            GinIndex(fields=['name'], name='subregion_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['asciiname'], name='subregion_asciiname_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['location_source'], name='subregion_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
        ]
        unique_together = ['name', 'region']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate subregion data."""
        if not self.name:
            raise ValidationError("Subregion name is required.")
        if not hasattr(self, 'region') or self.region is None:
            raise ValidationError("Region is required for a subregion.")
        if self.code and not self.code.isascii():
            raise ValidationError(f"Admin2 code must be ASCII, got {self.code}")
        if self.code and len(self.code) > 20:
            raise ValidationError(f"Admin2 code must be 20 characters or less, got {self.code}")
        self.name = normalize_text(self.name)
        if self.asciiname:
            self.asciiname = normalize_text(self.asciiname)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    # @transaction.atomic
    # def save(self, *args, user=None, skip_validation=False, **kwargs):
    #     """Save subregion with normalized fields."""
    #     logger.debug(f"Saving CustomSubRegion: {self.name}, user={user}")
    #     if not skip_validation:
    #         self.clean()
    #     User = get_user_model()
    #     if user and isinstance(user, User):
    #         if not self.pk:
    #             self.created_by = user
    #         self.updated_by = user
    #     if not self.slug:
    #         self.slug = slugify(self.name)
    #     try:
    #         super().save(*args, **kwargs)
    #         logger.info(f"Successfully saved CustomSubRegion: {self.name} (ID: {self.pk})")
    #     except Exception as e:
    #         logger.error(f"Failed to save CustomSubRegion: {self.name}, error: {str(e)}", exc_info=True)
    #         raise ValidationError(f"Failed to save subregion: {str(e)}")
    #     return self

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save subregion with normalized fields."""
        logger.debug(f"Saving CustomSubRegion: {self.name}, user={user}")

        if not skip_validation:
            self.clean()

        # Handle audit fields
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user

        if not self.slug:
            self.slug = slugify(self.name)

        try:
            # VERY IMPORTANT: call parent save cooperatively
            super(CustomSubRegion, self).save(*args, **kwargs)

            logger.info(f"Successfully saved CustomSubRegion: {self.name} (ID: {self.pk})")

        except Exception as e:
            logger.error(
                f"Failed to save CustomSubRegion: {self.name}, error: {str(e)}",
                exc_info=True
            )
            raise ValidationError(f"Failed to save subregion: {str(e)}")

        return self


    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete subregion."""
        logger.info(f"Soft deleting CustomSubRegion: {self.name}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive subregion.",
                code="inactive_subregion",
                details={"subregion_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted CustomSubRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete CustomSubRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete subregion: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted subregion."""
        logger.info(f"Restoring CustomSubRegion: {self.name}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active subregion.",
                code="already_active_subregion",
                details={"subregion_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored CustomSubRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore CustomSubRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore subregion: {str(e)}")

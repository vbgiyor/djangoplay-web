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

logger = logging.getLogger(__name__)

class GlobalRegion(TimeStampedModel, AuditFieldsModel):

    """Global region model."""

    code = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=100, unique=True)
    asciiname = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    objects = ActiveManager()
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of the global region data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    class Meta:
        app_label = 'locations'
        verbose_name = "Global Region"
        verbose_name_plural = "Global Regions"
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_global_region_name'
            ),
        ]
        indexes = [
            models.Index(fields=['name', 'slug']),
            GinIndex(fields=['name'], name='global_region_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['asciiname'], name='global_regn_asciiname_trgm_idx', opclasses=['gin_trgm_ops']),
            models.Index(fields=['geoname_id'], name='global_region_geoname_id_idx'),
            GinIndex(fields=['location_source'], name='global_region_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Validate global region data."""
        if not self.name:
            raise ValidationError("Global region name is required.")
        self.name = normalize_text(self.name)
        if self.asciiname:
            self.asciiname = normalize_text(self.asciiname)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save global region with normalized fields."""
        logger.debug(f"Saving GlobalRegion: {self.name}, user={user}")
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
            logger.info(f"Successfully saved GlobalRegion: {self.name} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save GlobalRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to save global region: {str(e)}")
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete global region."""
        logger.info(f"Soft deleting GlobalRegion: {self.name}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive global region.",
                code="inactive_global_region",
                details={"global_region_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted GlobalRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete GlobalRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete global region: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted global region."""
        logger.info(f"Restoring GlobalRegion: {self.name}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active global region.",
                code="already_active_global_region",
                details={"global_region_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored GlobalRegion: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore GlobalRegion: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore global region: {str(e)}")

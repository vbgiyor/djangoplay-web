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

class CustomCountry(TimeStampedModel, AuditFieldsModel):

    """Country model based on Geonames database with extended fields."""

    geoname_id = models.IntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=100, unique=True, help_text="Name of the country")
    asciiname = models.CharField(max_length=100, blank=True, null=True)
    alternatenames = models.TextField(blank=True, null=True, help_text="Comma-separated list of alternate names")
    country_code = models.CharField(max_length=2, blank=True, null=True, help_text="ISO-3166 2-letter country code")
    country_capital = models.CharField(max_length=100, blank=True, null=True, help_text="Capital city of the country")
    currency_symbol = models.CharField(max_length=10, blank=True, null=True, help_text="Currency symbol (e.g., ₹)")
    currency_code = models.CharField(max_length=3, blank=True, null=True, help_text="ISO 4217 currency code (e.g., INR)")
    currency_name = models.CharField(max_length=50, blank=True, null=True, help_text="Currency name (e.g., Indian Rupee)")
    country_phone_code = models.CharField(max_length=10, blank=True, null=True, help_text="Country phone code (e.g., +91)")
    postal_code_regex = models.CharField(max_length=300, blank=True, null=True, help_text="Regex for postal code validation")
    country_languages = models.TextField(max_length=300, blank=True, null=True, help_text="Comma-separated list of language codes (e.g., hi,en)")
    population = models.BigIntegerField(null=True, blank=True, help_text="Country population")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    global_regions = models.ManyToManyField('locations.GlobalRegion', related_name='countries', blank=True)
    has_postal_code = models.BooleanField(default=True)
    postal_code_length = models.CharField(max_length=20, null=True, blank=True, help_text="Maximum postal code length allowed for given country")
    phone_number_length = models.CharField(max_length=20, null=True, blank=True, help_text="Maximum phone number length allowed for given country")
    admin_codes = models.JSONField(blank=True, null=True, help_text="JSON object storing admin codes, e.g., {'admin1_codes': ['13', '14'], 'admin2_codes': ['594'], ...}" )
    location_source = models.CharField(max_length=50, blank=True, null=True, help_text="Source of the country data (e.g., 'geonames', 'GOI')")
    history = HistoricalRecords()

    objects = ActiveManager()

    class Meta:
        app_label = 'locations'
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_country_name'
            ),
            models.CheckConstraint(
                check=models.Q(population__gte=0),
                name='non_negative_population'
            ),
        ]
        indexes = [
            models.Index(fields=['geoname_id']),
            models.Index(fields=['name', 'slug', 'geoname_id', 'country_code']),
            GinIndex(fields=['name'], name='country_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['asciiname'], name='country_asciiname_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['alternatenames'], name='country_alternatename_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['location_source'], name='country_loc_src_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name

    def has_subregions(self):
        return CustomSubRegion.objects.filter(region__country=self).exists()

    def clean(self):
        """Validate country data."""
        if not self.name:
            raise ValidationError("Country name is required.")
        if self.country_code and len(self.country_code) != 2:
            raise ValidationError("Country code must be 2 characters long.")
        self.name = normalize_text(self.name)
        if self.asciiname:
            self.asciiname = normalize_text(self.asciiname)
        if self.location_source:
            self.location_source = normalize_text(self.location_source)

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save country with normalized fields."""
        logger.debug(f"Saving CustomCountry: {self.name}, user={user}")
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
            logger.info(f"Successfully saved CustomCountry: {self.name} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save CustomCountry: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to save country: {str(e)}")
        return self


    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete country."""
        logger.info(f"Soft deleting CustomCountry: {self.name}, user={user}")
        if not self.is_active:
            raise ValidationError(
                "Cannot perform operation on an inactive country.",
                code="inactive_country",
                details={"country_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().save()
            logger.info(f"Successfully soft deleted CustomCountry: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete CustomCountry: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to soft delete country: {str(e)}")

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted country."""
        logger.info(f"Restoring CustomCountry: {self.name}, user={user}")
        if self.is_active:
            raise ValidationError(
                "Cannot restore an active country.",
                code="already_active_country",
                details={"country_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        self.updated_by = user
        try:
            super().save()
            logger.info(f"Successfully restored CustomCountry: {self.name}, is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore CustomCountry: {self.name}, error: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to restore country: {str(e)}")

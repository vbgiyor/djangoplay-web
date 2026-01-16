import logging
from contextlib import contextmanager

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from fincore.constants import TAX_IDENTIFIER_TYPE_CHOICES
from fincore.exceptions import InactiveFincoreError, TaxProfileValidationError
from locations.models.custom_country import CustomCountry
from locations.models.custom_region import CustomRegion
from simple_history.models import HistoricalRecords
from utilities.utils.entities.entity_validations import is_valid_indian_pan, validate_gstin
from utilities.utils.general.normalize_text import normalize_text

logger = logging.getLogger(__name__)

class TaxProfile(TimeStampedModel, AuditFieldsModel):

    """Model for storing tax identifiers and exemption details for Entities."""

    _is_soft_deleting = False  # Class-level flag to track soft deletion

    entity_mapping = models.ForeignKey(
        'fincore.FincoreEntityMapping',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fincore_entity_tax_profiles',
        help_text="Entity mapping associated with this tax profile."
    )
    tax_identifier = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tax identifier (e.g., GSTIN, VAT, EIN)."
    )
    tax_identifier_type = models.CharField(
        max_length=20,
        choices=TAX_IDENTIFIER_TYPE_CHOICES,
        default='GSTIN',
        help_text="Type of tax identifier."
    )
    is_tax_exempt = models.BooleanField(
        default=False,
        help_text="Whether the entity is tax-exempt."
    )
    tax_exemption_reason = models.TextField(
        blank=True,
        help_text="Reason for tax exemption, if applicable."
    )
    tax_exemption_document = models.FileField(
        upload_to='tax_exemptions/',
        blank=True,
        null=True,
        help_text="Document supporting tax exemption, if applicable."
    )
    country = models.ForeignKey(
        CustomCountry,
        on_delete=models.PROTECT,
        related_name='tax_profiles',
        help_text="Country associated with the tax profile."
    )
    region = models.ForeignKey(
        CustomRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tax_profiles',
        help_text="Region or state associated with the tax profile."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'tax_profile'
        ordering = ['tax_identifier_type', 'country__country_code']
        verbose_name = "Tax Profile"
        verbose_name_plural = "Tax Profiles"
        constraints = [
            models.UniqueConstraint(
                fields=['entity_mapping', 'tax_identifier', 'tax_identifier_type'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_tax_profile'
            ),
            models.CheckConstraint(
                check=Q(tax_identifier_type__in=[choice[0] for choice in TAX_IDENTIFIER_TYPE_CHOICES]),
                name='valid_tax_identifier_type'
            ),
        ]
        indexes = [
            models.Index(fields=['entity_mapping', 'tax_identifier_type', 'is_tax_exempt'], name='tax_ent_type_exm_idx'),
            models.Index(fields=['tax_identifier']),
            models.Index(fields=['country']),
            models.Index(fields=['region']),
            models.Index(fields=['is_tax_exempt']),
            GinIndex(fields=['tax_identifier'], name='tax_id_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"{self.get_tax_identifier_type_display()} ({self.tax_identifier}) for {self.entity_mapping or 'Unassigned'}"

    def get_cached_country(self):
        """Retrieve country from cache or database."""
        cache_key = f"country_{self.country_id}"
        country = cache.get(cache_key)
        if not country:
            country = self.country
            cache.set(cache_key, country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        return country

    def get_cached_region(self):
        """Retrieve region from cache or database."""
        if not self.region:
            return None
        cache_key = f"region_{self.region_id}"
        region = cache.get(cache_key)
        if not region:
            region = self.region
            cache.set(cache_key, region, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        return region

    def get_cached_entity_mapping(self):
        """Retrieve entity mapping from cache or database."""
        if not self.entity_mapping:
            return None
        cache_key = f"entity_mapping_{self.entity_mapping_id}"
        mapping = cache.get(cache_key)
        if not mapping:
            mapping = self.entity_mapping
            cache.set(cache_key, mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        return mapping

    def clean(self):
        logger.debug(f"Validating TaxProfile: {self.tax_identifier}")
        if self.deleted_at:
            raise InactiveFincoreError(details={"object": "TaxProfile", "id": self.id})
        if not self.entity_mapping:
            raise TaxProfileValidationError("Tax profile must be associated with an entity mapping.", code="missing_entity_mapping")
        if not self.country:
            raise TaxProfileValidationError("Country is required.", code="missing_country")
        country = self.get_cached_country()
        region = self.get_cached_region()
        if region and region.country != country:
            raise TaxProfileValidationError("Region must belong to the same country as the tax profile.", code="invalid_region")
        if self.tax_identifier and self.tax_identifier_type == 'GSTIN':
            try:
                validate_gstin(self.tax_identifier)
            except ValidationError as e:
                raise TaxProfileValidationError(f"Invalid GSTIN: {str(e)}", code="invalid_gstin")
        if self.tax_identifier and self.tax_identifier_type == 'PAN':
            if not is_valid_indian_pan(self.tax_identifier):
                raise TaxProfileValidationError("Invalid PAN format.", code="invalid_pan")
        if self.is_tax_exempt and not self.tax_exemption_reason:
            raise TaxProfileValidationError("Tax exemption reason is required if tax-exempt.", code="missing_exemption_reason")
        if self.tax_identifier_type != 'OTHER' and not self.tax_identifier:
            raise TaxProfileValidationError(f"Tax identifier is required for {self.tax_identifier_type}.", code="missing_tax_identifier")
        if self.tax_identifier:
            self.tax_identifier = normalize_text(self.tax_identifier)
        if self.tax_exemption_reason:
            self.tax_exemption_reason = normalize_text(self.tax_exemption_reason)
        super().clean()

    @transaction.atomic
    def save(self, *args, user=None, **kwargs):
        """Save tax profile with audit logging and cache update."""
        logger.debug(f"Saving TaxProfile: {self.tax_identifier}, user={user}")
        if not TaxProfile._is_soft_deleting:  # Assuming similar flag
            self.clean()
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        cache.set(f"country_{self.country_id}", self.country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if self.region:
            cache.set(f"region_{self.region_id}", self.region, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if self.entity_mapping:
            cache.set(f"entity_mapping_{self.entity_mapping_id}", self.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.info(f"TaxProfile saved: {self} (ID: {self.pk})")

    @contextmanager
    def _soft_delete_context(self):
        """
        Context manager to set soft deletion flag.
        """
        TaxProfile._is_soft_deleting = True
        try:
            yield
        finally:
            TaxProfile._is_soft_deleting = False

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete tax profile."""
        logger.info(f"Soft deleting TaxProfile: {self}, user={user}")
        with self._soft_delete_context():  # Assuming similar context manager
            self.deleted_by = user
            self.deleted_at = timezone.now()
            self.is_active = False
            super().save(update_fields=['deleted_at', 'deleted_by', 'is_active'])

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted tax profile."""
        logger.info(f"Restoring TaxProfile: {self}, user={user}")
        super().restore()
        self.updated_by = user
        self.save()

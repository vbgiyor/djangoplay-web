import logging
from contextlib import contextmanager

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.apps import apps
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from fincore.constants import ADDRESS_TYPE_CHOICES
from fincore.exceptions import AddressValidationError, InactiveFincoreError
from locations.models.custom_city import CustomCity
from locations.models.custom_country import CustomCountry
from locations.models.custom_region import CustomRegion
from locations.models.custom_subregion import CustomSubRegion
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.postal_code_validations import validate_postal_code

logger = logging.getLogger(__name__)

class Address(TimeStampedModel, AuditFieldsModel):

    """Model for storing structured addresses for Entities."""

    _is_soft_deleting = False  # Class-level flag to track soft deletion

    entity_mapping = models.ForeignKey(
        'fincore.FincoreEntityMapping',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fincore_entity_addresses',
        help_text="Entity mapping associated with this address."
    )
    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default='BILLING',
        help_text="Type of address (e.g., Billing, Shipping)."
    )
    street_address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Street address, mapped to Location.street_address."
    )
    city = models.ForeignKey(
        CustomCity,
        on_delete=models.PROTECT,
        related_name='addresses',
        help_text="City where the address is located."
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Postal code for the address, validated per country."
    )
    country = models.ForeignKey(
        CustomCountry,
        on_delete=models.PROTECT,
        related_name='addresses',
        help_text="Country where the address is located."
    )
    region = models.ForeignKey(
        CustomRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='addresses',
        help_text="Region or state where the address is located."
    )
    subregion = models.ForeignKey(
        CustomSubRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='addresses',
        help_text="Subregion or district where the address is located."
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default address for the entity."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'address'
        ordering = ['city__name', 'address_type']
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        constraints = [
            models.UniqueConstraint(
                fields=['entity_mapping', 'address_type', 'street_address', 'city'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_address'
            ),
            models.CheckConstraint(
                check=Q(address_type__in=[choice[0] for choice in ADDRESS_TYPE_CHOICES]),
                name='valid_address_type'
            ),
        ]
        indexes = [
            models.Index(fields=['entity_mapping', 'address_type', 'is_default'], name='addr_ent_type_def_idx'),
            models.Index(fields=['city', 'country']),
            models.Index(fields=['is_default']),
            GinIndex(fields=['street_address'], name='address_street_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['postal_code'], name='address_postal_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    # def __str__(self):
    #     entity_name = "Unassigned"
    #     if self.entity_mapping:
    #         try:
    #             # Dynamically load model from entity_type string
    #             app_label, model_name = self.entity_mapping.entity_type.split(".")
    #             model_cls = apps.get_model(app_label, model_name)
    #             obj = model_cls.objects.filter(pk=self.entity_mapping.entity_id).only("name").first()
    #             if obj and hasattr(obj, "name"):
    #                 entity_name = obj.name
    #         except Exception:
    #             entity_name = str(self.entity_mapping)  # fallback

    #     return f"{self.get_address_type_display()} for {entity_name}"

    def __str__(self):
        entity_name = "Unassigned"
        if self.entity_mapping:
            cache_key = f"entity_name:{self.entity_mapping.entity_type}:{self.entity_mapping.entity_id}"
            entity_name = cache.get(cache_key)
            if not entity_name:
                try:
                    app_label, model_name = self.entity_mapping.entity_type.split(".")
                    model_cls = apps.get_model(app_label, model_name)
                    obj = model_cls.objects.filter(pk=self.entity_mapping.entity_id).only("name").first()
                    if obj and hasattr(obj, "name"):
                        entity_name = obj.name
                        cache.set(cache_key, entity_name, timeout=3600)
                except Exception:
                    entity_name = str(self.entity_mapping)
        return f"{self.get_address_type_display()} for {entity_name}"


    def get_full_address(self):
        """Return a formatted string of the full address."""
        parts = [self.street_address, self.get_cached_city().name]
        if self.subregion:
            parts.append(self.get_cached_subregion().name)
        if self.region:
            parts.append(self.get_cached_region().name)
        parts.append(self.get_cached_country().name)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(part for part in parts if part)

    def get_cached_city(self):
        """Retrieve city from cache or database."""
        cache_key = f"city_{self.city_id}"
        city = cache.get(cache_key)
        if not city:
            city = self.city
            cache.set(cache_key, city, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        return city

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

    def get_cached_subregion(self):
        """Retrieve subregion from cache or database."""
        if not self.subregion:
            return None
        cache_key = f"subregion_{self.subregion_id}"
        subregion = cache.get(cache_key)
        if not subregion:
            subregion = self.subregion
            cache.set(cache_key, subregion, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        return subregion

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

    @contextmanager
    def _soft_delete_context(self):
        """
        Context manager to set soft deletion flag.
        """
        Address._is_soft_deleting = True
        try:
            yield
        finally:
            Address._is_soft_deleting = False

    def clean(self):
        """
        Validate the address, but skip validation during soft deletion.
        """
        if Address._is_soft_deleting:
            logger.debug("Skipping Address.clean() during soft_delete")
            return  # Bypass validation during soft_delete

        logger.debug(f"Validating Address for {self.entity_mapping or 'Unassigned'}")
        if self.deleted_at:
            raise InactiveFincoreError(details={"object": "Address", "id": self.id})
        if not self.entity_mapping:
            raise AddressValidationError("Address must be associated with an entity mapping.", code="missing_entity_mapping")
        if not self.city:
            raise AddressValidationError("City is required.", code="missing_city")
        if not self.country:
            raise AddressValidationError("Country is required.", code="missing_country")
        if self.address_type == 'HEADQUARTERS' and not self.street_address:
            raise AddressValidationError("Street address is required for HEADQUARTERS address type.", code="missing_street_address")
        city = self.get_cached_city()
        country = self.get_cached_country()
        region = self.get_cached_region()
        subregion = self.get_cached_subregion()
        if subregion and subregion.region.country != city.subregion.region.country:
            raise AddressValidationError("Subregion must belong to the same country as the city.", code="invalid_subregion")
        if region and region.country != city.subregion.region.country:
            raise AddressValidationError("Region must belong to the same country as the city.", code="invalid_region")
        if self.postal_code:
            try:
                validate_postal_code(self.postal_code, country.country_code)
            except ValidationError as e:
                raise AddressValidationError(f"Invalid postal code: {str(e)}", code="invalid_postal_code")
        if self.street_address:
            self.street_address = normalize_text(self.street_address)

        super().clean()

    @transaction.atomic
    def save(self, *args, user=None, **kwargs):
        """Save address with audit logging and cache update."""
        logger.debug(f"Saving Address for {self.entity_mapping or 'Unassigned'}, user={user}")
        if not Address._is_soft_deleting:
            self.clean()  # Only call clean if not soft deleting
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        cache.set(f"city_{self.city_id}", self.city, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        cache.set(f"country_{self.country_id}", self.country, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if self.region:
            cache.set(f"region_{self.region_id}", self.region, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if self.subregion:
            cache.set(f"subregion_{self.subregion_id}", self.subregion, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        if self.entity_mapping:
            cache.set(f"entity_mapping_{self.entity_mapping_id}", self.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.info(f"Address saved: {self} (ID: {self.pk})")

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete address."""
        logger.info(f"Soft deleting Address: {self}, user={user}")
        with self._soft_delete_context():
            self.deleted_by = user
            self.deleted_at = timezone.now()
            self.is_active = False  # Align with TimeStampedModel
            super().save(update_fields=['deleted_at', 'deleted_by', 'is_active'])

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted address."""
        logger.info(f"Restoring Address: {self}, user={user}")
        super().restore()
        self.updated_by = user
        self.save()

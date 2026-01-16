import logging
import re
from contextlib import contextmanager

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from fincore.models.address import Address
from fincore.models.contact import Contact
from fincore.models.entity_mapping import FincoreEntityMapping
from fincore.models.tax_profile import TaxProfile
from industries.models import Industry
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords
from utilities.utils.entities.entity_validations import is_valid_indian_pan, validate_gstin
from utilities.utils.general.normalize_text import normalize_text

from entities.constants import ENTITY_STATUS_CHOICES, ENTITY_TYPE_CHOICES
from entities.exceptions import EntityValidationError, InactiveEntityError, IndianTaxComplianceError

logger = logging.getLogger(__name__)


class Entity(MPTTModel, TimeStampedModel, AuditFieldsModel):

    """Model representing an entity (e.g., organization, individual) in the system."""

    _is_soft_deleting = False
    name = models.CharField(
        max_length=255,
        help_text="Name of the entity (e.g., company name, individual name)."
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier for the entity."
    )
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        default="BUSINESS",
        blank=True,           # <-- added
        help_text="Type of entity..."
    )
    status = models.CharField(
        max_length=20,
        choices=ENTITY_STATUS_CHOICES,
        default="ACTIVE",
        blank=True,           # <-- added
        help_text="Status of the entity..."
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
        help_text="External identifier for integration with other systems."
    )
    website = models.URLField(
        max_length=200,
        blank=True,
        help_text="Entity's website URL."
    )
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Registration number (e.g., CIN, GSTIN, EIN)."
    )
    entity_size = models.CharField(
        max_length=50,
        blank=True,
        help_text="Size of the entity (e.g., Small, Medium, Large)."
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the entity."
    )
    default_address = models.ForeignKey(
        'fincore.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_for_entities',
        help_text="Default address for the entity."
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text="Parent entity in the organizational hierarchy."
    )
    industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entities',
        help_text="Industry classification for the entity."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'entity'
        ordering = ['name']
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'entity_type'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_entity_name_type'
            ),
            models.CheckConstraint(
                check=Q(entity_type__in=[choice[0] for choice in ENTITY_TYPE_CHOICES]),
                name='valid_entity_type'
            ),
            models.CheckConstraint(
                check=Q(status__in=[choice[0] for choice in ENTITY_STATUS_CHOICES]),
                name='valid_entity_status'
            ),
        ]
        indexes = [
            models.Index(fields=['name', 'entity_type', 'status'], name='entity_name_type_status_idx'),
            models.Index(fields=['name', 'slug'], name='entity_name_slug_idx'),
            models.Index(fields=['external_id'], name='entity_ext_id_idx'),
            models.Index(fields=['created_by'], name='entity_created_by_idx'),
            models.Index(fields=['updated_by'], name='entity_updated_by_idx'),
            models.Index(fields=['deleted_by'], name='entity_deleted_by_idx'),
            GinIndex(fields=['name'], name='entity_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['registration_number'], name='entity_reg_number_trgm_idx', opclasses=['gin_trgm_ops']),
            models.Index(fields=['industry'], name='entity_industry_idx'),
            models.Index(fields=['status'], name='entity_status_idx'),
            models.Index(fields=['default_address'], name='entity_default_address_idx'),
            models.Index(fields=['slug'], name='entity_slug_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_entity_type_display()})"

    def get_entity_mapping(self):
        """Retrieve or create the FincoreEntityMapping for this entity."""
        mapping, created = FincoreEntityMapping.objects.get_or_create(
            entity_type='entities.Entity',
            entity_id=str(self.id),
            defaults={'content_type': 'entities.Entity'}
        )
        return mapping

    def get_addresses(self):
        """Retrieve addresses associated with this entity via FincoreEntityMapping."""
        return Address.objects.filter(entity_mapping=self.get_entity_mapping())

    def get_headquarter_location(self):
        """Retrieve the headquarters address for the entity."""
        if self.default_address and self.default_address.address_type == 'HEADQUARTERS':
            return self.default_address.get_cached_city()
        return '-'

    def get_country(self):
        """Retrieve the country for the entity."""
        if self.default_address and self.default_address.country:
            return self.default_address.get_cached_country()
        return '-'

    def get_contacts(self):
        """Retrieve contacts associated with this entity via FincoreEntityMapping."""
        return Contact.objects.filter(entity_mapping=self.get_entity_mapping())

    def get_tax_profiles(self):
        """Retrieve tax profiles associated with this entity via FincoreEntityMapping."""
        return TaxProfile.objects.filter(entity_mapping=self.get_entity_mapping())

    @transaction.atomic
    def add_address(self, address, user=None):
        """Add an address to the entity."""
        if not isinstance(address, Address):
            raise EntityValidationError("Invalid address provided.", code="invalid_address")
        if address.deleted_at:
            raise EntityValidationError("Cannot add a deleted address.", code="invalid_address")
        address.entity_mapping = self.get_entity_mapping()
        address.save(user=user)
        logger.info(f"Added address {address} to entity {self}")

    @transaction.atomic
    def remove_address(self, address, user=None):
        """Remove an address from the entity."""
        if not isinstance(address, Address):
            raise EntityValidationError("Invalid address provided.", code="invalid_address")
        if self.default_address == address:
            raise EntityValidationError(
                "Cannot remove the default address.",
                code="remove_default_address",
                details={"address_id": address.id}
            )
        if address.entity_mapping != self.get_entity_mapping():
            raise EntityValidationError(
                "Address is not associated with this entity.",
                code="invalid_address",
                details={"address_id": address.id}
            )
        address.soft_delete(user=user)
        logger.info(f"Removed address {address} from entity {self}")

    @transaction.atomic
    def set_default_address(self, address, user=None):
        """Set the default address for the entity."""
        if not isinstance(address, Address):
            raise EntityValidationError("Invalid address provided.", code="invalid_address")
        if address.deleted_at:
            raise EntityValidationError("Cannot set a deleted address as default.", code="invalid_address")
        if address.entity_mapping != self.get_entity_mapping():
            raise EntityValidationError(
                "Address is not associated with this entity.",
                code="invalid_address",
                details={"address_id": address.id}
            )
        self.default_address = address
        self.save(user=user)
        logger.info(f"Set default address {address} for entity {self}")

    @transaction.atomic
    def add_contact(self, contact, user=None):
        """Add a contact to the entity."""
        if not isinstance(contact, Contact):
            raise EntityValidationError("Invalid contact provided.", code="invalid_contact")
        if contact.deleted_at:
            raise EntityValidationError("Cannot add a deleted contact.", code="invalid_contact")
        contact.entity_mapping = self.get_entity_mapping()
        contact.save(user=user)
        logger.info(f"Added contact {contact} to entity {self}")

    @transaction.atomic
    def remove_contact(self, contact, user=None):
        """Remove a contact from the entity."""
        if not isinstance(contact, Contact):
            raise EntityValidationError("Invalid contact provided.", code="invalid_contact")
        if contact.entity_mapping != self.get_entity_mapping():
            raise EntityValidationError(
                "Contact is not associated with this entity.",
                code="invalid_contact",
                details={"contact_id": contact.id}
            )
        contact.soft_delete(user=user)
        logger.info(f"Removed contact {contact} from entity {self}")

    @transaction.atomic
    def add_tax_profile(self, tax_profile, user=None):
        """Add a tax profile to the entity."""
        if not isinstance(tax_profile, TaxProfile):
            raise EntityValidationError("Invalid tax profile provided.", code="invalid_tax_profile")
        if tax_profile.deleted_at:
            raise EntityValidationError("Cannot add a deleted tax profile.", code="invalid_tax_profile")
        tax_profile.entity_mapping = self.get_entity_mapping()
        tax_profile.save(user=user)
        logger.info(f"Added tax profile {tax_profile} to entity {self}")

    @transaction.atomic
    def remove_tax_profile(self, tax_profile, user=None):
        """Remove a tax profile from the entity."""
        if not isinstance(tax_profile, TaxProfile):
            raise EntityValidationError("Invalid tax profile provided.", code="invalid_tax_profile")
        if tax_profile.entity_mapping != self.get_entity_mapping():
            raise EntityValidationError(
                "Tax profile is not associated with this entity.",
                code="invalid_tax_profile",
                details={"tax_profile_id": tax_profile.id}
            )
        tax_profile.soft_delete(user=user)
        logger.info(f"Removed tax profile {tax_profile} from entity {self}")

    @transaction.atomic
    def clean(self):
        """Validate entity fields and relationships."""
        logger.debug(f"Validating Entity: {self.name or 'New Entity'}")
        if self.deleted_at:
            raise InactiveEntityError(details={"object": "Entity", "id": self.id})
        if not self.name or not self.name.strip():
            raise EntityValidationError("Entity name cannot be empty.", code="missing_name")

        # Normalize text fields
        for field in ['name', 'slug', 'registration_number', 'entity_size', 'notes']:
            value = getattr(self, field, None)
            if value:
                setattr(self, field, normalize_text(value))

        # Generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name)
            if Entity.objects.filter(slug=self.slug, deleted_at__isnull=True).exclude(pk=self.pk).exists():
                raise EntityValidationError(
                    f"Slug {self.slug} is already in use.",
                    code="duplicate_name",
                    details={"field": "slug", "value": self.slug}
                )

        # Validate website
        if self.website and not re.match(r'^https?://', self.website):
            self.website = f'https://{self.website}'

        # Validate entity_type and status
        if self.entity_type not in dict(ENTITY_TYPE_CHOICES):
            raise EntityValidationError(
                f"Invalid entity type: {self.entity_type}.",
                code="invalid_entity_type",
                details={"field": "entity_type", "value": self.entity_type}
            )
        if self.status not in dict(ENTITY_STATUS_CHOICES):
            raise EntityValidationError(
                f"Invalid status: {self.status}.",
                code="invalid_status",
                details={"field": "status", "value": self.status}
            )

        # Validate default address
        if self.default_address:
            if self.default_address.entity_mapping != self.get_entity_mapping():
                raise EntityValidationError(
                    "Default address must be associated with this entity.",
                    code="invalid_default_address",
                    details={"address_id": self.default_address.id}
                )
            if self.entity_type in ('BUSINESS', 'GOVERNMENT', 'NONPROFIT', 'PARTNERSHIP') and \
               self.default_address.address_type != 'HEADQUARTERS':
                raise EntityValidationError(
                    "Default address for BUSINESS, GOVERNMENT, NONPROFIT, and PARTNERSHIP must be of type HEADQUARTERS.",
                    code="invalid_default_address",
                    details={"address_type": self.default_address.address_type}
                )

        # Validate industry
        if self.entity_type in ('BUSINESS', 'GOVERNMENT', 'NONPROFIT', 'PARTNERSHIP') and not self.industry:
            raise EntityValidationError(
                "Industry is required for BUSINESS, GOVERNMENT, NONPROFIT, and PARTNERSHIP entities.",
                code="invalid_industry",
                details={"field": "industry"}
            )

        # Validate registration number for Indian entities
        if self.registration_number and self.entity_type in ('BUSINESS', 'PARTNERSHIP'):
            tax_profiles = self.get_tax_profiles().filter(tax_identifier_type__in=['GSTIN', 'PAN'])
            for tax_profile in tax_profiles:
                if tax_profile.tax_identifier_type == 'GSTIN':
                    try:
                        validate_gstin(tax_profile.tax_identifier)
                        # Check GSTIN state code against default address
                        if self.default_address and self.default_address.city:
                            state_code = tax_profile.tax_identifier[:2]
                            if state_code != self.default_address.city.subregion.region.code:
                                raise IndianTaxComplianceError(
                                    "GSTIN state code does not match the default address state.",
                                    code="gstin_state_mismatch",
                                    details={"gstin": tax_profile.tax_identifier, "state": self.default_address.city.subregion.region.name}
                                )
                    except ValidationError as e:
                        raise IndianTaxComplianceError(
                            f"Invalid GSTIN: {str(e)}",
                            code="missing_gstin",
                            details={"tax_identifier": tax_profile.tax_identifier}
                        )
                elif tax_profile.tax_identifier_type == 'PAN' and not is_valid_indian_pan(tax_profile.tax_identifier):
                    raise IndianTaxComplianceError(
                        "Invalid PAN format.",
                        code="missing_pan",
                        details={"tax_identifier": tax_profile.tax_identifier}
                    )

        super().clean()

    @transaction.atomic
    def save(self, *args, user=None, skip_mapping=False, **kwargs):
        """Save entity with audit logging and slug generation."""
        logger.debug(f"Saving Entity: {self.name}, user={user}")
        if not Entity._is_soft_deleting:
            self.clean()
        if not self.slug:
            self.slug = slugify(self.name)
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        if not skip_mapping:
            self.get_entity_mapping()
        logger.info(f"Entity saved: {self} (ID: {self.pk})")

    @contextmanager
    def _soft_delete_context(self):
        Entity._is_soft_deleting = True
        try:
            yield
        finally:
            Entity._is_soft_deleting = False

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete entity and associated resources."""
        logger.info(f"Soft deleting Entity: {self}, user={user}")
        with self._soft_delete_context():  # Add context manager if not present
            self.deleted_by = user
            self.deleted_at = timezone.now()
            self.is_active = False
            # Soft delete associated addresses, contacts, and tax profiles
            for address in self.get_addresses():
                address.soft_delete(user=user)
            for contact in self.get_contacts():
                contact.soft_delete(user=user)
            for tax_profile in self.get_tax_profiles():
                tax_profile.soft_delete(user=user)
            super().save(update_fields=['deleted_at', 'deleted_by', 'is_active'])

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted entity and associated resources."""
        logger.info(f"Restoring Entity: {self}, user={user}")
        super().restore()
        self.updated_by = user
        self.save()
        # Restore associated resources
        for address in self.get_addresses().filter(deleted_at__isnull=False):
            address.restore(user=user)
        for contact in self.get_contacts().filter(deleted_at__isnull=False):
            contact.restore(user=user)
        for tax_profile in self.get_tax_profiles().filter(deleted_at__isnull=False):
            tax_profile.restore(user=user)

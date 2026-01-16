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
from fincore.constants import CONTACT_ROLE_CHOICES
from fincore.exceptions import ContactValidationError, InactiveFincoreError
from locations.models.custom_country import CustomCountry
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.phone_number_validations import validate_phone_number

logger = logging.getLogger(__name__)

class Contact(TimeStampedModel, AuditFieldsModel):

    """Model for storing contact details for Entities."""

    _is_soft_deleting = False  # Class-level flag to track soft deletion

    entity_mapping = models.ForeignKey(
        'fincore.FincoreEntityMapping',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fincore_entity_contacts',
        help_text="Entity mapping associated with this contact."
    )
    name = models.CharField(
        max_length=255,
        help_text="Full name of the contact."
    )
    email = models.EmailField(
        blank=True,
        help_text="Email address of the contact."
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone_number],
        help_text="Phone number in international format (e.g., +1234567890)."
    )
    role = models.CharField(
        max_length=20,
        choices=CONTACT_ROLE_CHOICES,
        default='PRIMARY',
        help_text="Role of the contact (e.g., Billing, Technical)."
    )
    country = models.ForeignKey(
        CustomCountry,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='contacts',
        help_text="Country associated with the contact for phone number validation."
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary contact for the entity."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'contact'
        ordering = ['name', 'role']
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        constraints = [
            models.UniqueConstraint(
                fields=['entity_mapping', 'email', 'role'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_contact'
            ),
            models.CheckConstraint(
                check=Q(role__in=[choice[0] for choice in CONTACT_ROLE_CHOICES]),
                name='valid_contact_role'
            ),
        ]
        indexes = [
            models.Index(fields=['entity_mapping', 'role', 'is_primary'], name='cont_ent_role_prim_idx'),
            models.Index(fields=['email']),
            models.Index(fields=['country']),
            models.Index(fields=['is_primary']),
            GinIndex(fields=['name'], name='contact_name_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['email'], name='contact_email_trgm_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        country = f", {self.country.name}" if self.country else ""
        return f"{self.name} ({self.get_role_display()}) for {self.entity_mapping or 'Unassigned'}{country}"

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
        logger.debug(f"Validating Contact: {self.name}")
        if self.deleted_at:
            raise InactiveFincoreError(details={"object": "Contact", "id": self.id})
        if not self.entity_mapping:
            raise ContactValidationError("Contact must be associated with an entity mapping.", code="missing_entity_mapping")
        if not self.name or not self.name.strip():
            raise ContactValidationError("Contact name is required.", code="missing_name")
        if not self.email and not self.phone_number:
            raise ContactValidationError("At least one of email or phone number is required.", code="missing_contact_info")
        if self.phone_number:
            country_code = self.country.country_code if self.country and self.country.country_code else None
            try:
                validate_phone_number(self.phone_number, country_code)
            except ValidationError as e:
                raise ContactValidationError(f"Invalid phone number: {str(e)}", code="invalid_phone_number")
        if self.name:
            self.name = normalize_text(self.name)
        if self.email:
            self.email = normalize_text(self.email)
        super().clean()

    @transaction.atomic
    def save(self, *args, user=None, **kwargs):
        """Save contact with audit logging."""
        logger.debug(f"Saving Contact: {self.name}, user={user}")
        if not Contact._is_soft_deleting:  # Assuming similar flag
            self.clean()
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        if self.entity_mapping:
            cache.set(f"entity_mapping_{self.entity_mapping_id}", self.entity_mapping, timeout=getattr(settings, 'LOCATION_CACHE_TIMEOUT', 3600))
        logger.info(f"Contact saved: {self} (ID: {self.pk})")

    @contextmanager
    def _soft_delete_context(self):
        """
        Context manager to set soft deletion flag.
        """
        Contact._is_soft_deleting = True
        try:
            yield
        finally:
            Contact._is_soft_deleting = False

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete contact."""
        logger.info(f"Soft deleting Contact: {self}, user={user}")
        with self._soft_delete_context():  # Assuming similar context manager
            self.deleted_by = user
            self.deleted_at = timezone.now()
            self.is_active = False
            super().save(update_fields=['deleted_at', 'deleted_by', 'is_active'])

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted contact."""
        logger.info(f"Restoring Contact: {self}, user={user}")
        super().restore()
        self.updated_by = user
        self.save()

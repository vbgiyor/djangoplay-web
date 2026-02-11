import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)


class Address(TimeStampedModel, AuditFieldsModel):

    """
    Stores versioned address records.
    Exactly ONE active address per owner is allowed.
    """

    class AddressType(models.TextChoices):
        CURRENT = "CURRENT", "Current Address"
        PERMANENT = "PERMANENT", "Permanent Address"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="addresses",
        null=False,
        blank=False,
        help_text="Employee or Member owning this address",
    )

    address = models.TextField(
        help_text="Full address text"
    )

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
        help_text="Informational address type",
    )

    country = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name_plural = "Addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(is_active=True),
                name="one_active_address_per_owner",
            )
        ]

    def clean(self):
        if not self.address:
            raise ValidationError("Address is required.")
        if self.postal_code and not self.postal_code.strip():
            self.postal_code = None


    def __str__(self):
        return f"{self.owner.email} — {self.city or 'Unknown'}"

    def save(self, *args, user=None, **kwargs):
        """Save with audit fields."""
        logger.info(f"Saving Address: user={user}")
        self.clean()
        if user:
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
        logger.info(f"Address saved: {self}")

    def soft_delete(self, user=None, reason=None):
        """Soft delete address."""
        logger.info(f"Soft deleting Address: id={self.id}, user={user}, reason={reason}")
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.is_active = False
        self.save(user=user)  # This uses your overridden save() → sets updated_by

    def restore(self, user=None):
        """Restore a soft-deleted address."""
        logger.info(f"Restoring Address: id={self.id}, user={user}")
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True
        self.save(user=user)  # This is the fix — pass user so updated_by is set

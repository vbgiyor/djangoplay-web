import logging
import re

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import PAYMENT_METHOD_CODE_MAX_LENGTH, PAYMENT_METHOD_NAME_MAX_LENGTH
from invoices.exceptions import InvoiceValidationError

logger = logging.getLogger(__name__)

class PaymentMethod(TimeStampedModel, AuditFieldsModel):

    """Model representing available payment methods for invoices and payments."""

    id = models.AutoField(primary_key=True)
    code = models.CharField(
        max_length=PAYMENT_METHOD_CODE_MAX_LENGTH,
        unique=True,
        help_text="Unique code for the payment method (e.g., UPI, CREDIT_CARD)."
    )
    name = models.CharField(
        max_length=PAYMENT_METHOD_NAME_MAX_LENGTH,
        help_text="Display name of the payment method (e.g., Unified Payments Interface)."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional description of the payment method."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is currently available for use."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'payment_method'
        ordering = ['code']
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_payment_method'
            ),
        ]
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate payment method data."""
        logger.debug(f"Validating PaymentMethod: {self.code}")

        # Normalize text fields
        for field in ['code', 'name', 'description']:
            value = getattr(self, field, None)
            if value:
                setattr(self, field, normalize_text(value))

        if not re.match(r'^[a-zA-Z0-9_]+$', self.code):
            raise InvoiceValidationError(
                "Payment method code must be alphanumeric or contain underscores.",
                code="invalid_payment_method_code",
                details={"field": "code", "value": self.code}
            )

    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save payment method with audit logging."""
        logger.debug(f"Saving PaymentMethod: {self.code}, user={user}")
        if not skip_validation:
            self.clean()

        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user

        try:
            super().save(*args, **kwargs)
            logger.info(f"PaymentMethod saved successfully: {self} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save PaymentMethod: {self.code}, error: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to save payment method: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
        return self

    def soft_delete(self, user=None):
        """Soft delete payment method."""
        logger.info(f"Soft deleting PaymentMethod: {self.code}, user={user}")
        if not self.is_active:
            raise InvoiceValidationError(
                "Cannot perform operation on an inactive payment method.",
                code="inactive_payment_method",
                details={"method_id": self.id}
            )
        self.deleted_by = user
        self.is_active = False
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.code}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.code}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to soft delete payment method: {str(e)}",
                code="soft_delete_error",
                details={"error": str(e)}
            )

    def restore(self, user=None):
        """Restore a soft-deleted payment method."""
        logger.info(f"Restoring PaymentMethod: {self.code}, user={user}")
        try:
            super().restore()
            self.is_active = True
            self.updated_by = user
            self.save()
            logger.info(f"Successfully restored {self.code}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.code}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to restore payment method: {str(e)}",
                code="restore_error",
                details={"error": str(e)}
            )

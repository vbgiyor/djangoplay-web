import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models, transaction
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import STATUS_CODE_MAX_LENGTH, STATUS_NAME_MAX_LENGTH
from invoices.exceptions import InvalidInvoiceStatusError, InvoiceValidationError

logger = logging.getLogger(__name__)

class Status(TimeStampedModel, AuditFieldsModel):

    """Model representing possible statuses for an invoice."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=STATUS_NAME_MAX_LENGTH,
        unique=True,
        help_text="Display name of the status (e.g., 'Draft')."
    )
    code = models.CharField(
        max_length=STATUS_CODE_MAX_LENGTH,
        unique=True,
        help_text="Unique code for the status (e.g., 'DRAFT')."
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default status for new invoices."
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Whether invoices with this status are locked from edits."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'status'
        ordering = ['name']
        verbose_name = "Invoice Status"
        verbose_name_plural = "Invoice Statuses"
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_status_name'
            ),
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_status_code'
            ),
        ]
        indexes = [
            models.Index(fields=['name', 'code']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_locked']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        logger.debug(f"Validating InvoiceStatus: {self.name or 'Unnamed'}")
        if getattr(self, '_skip_validation', False):
            logger.debug("Skipping model validation for GET request")
            return
        if not self.name or not self.name.strip():
            logger.warning("Model validation failed: empty name")
            raise InvoiceValidationError(
                message="Status name cannot be empty or whitespace.",
                code="empty_name"
            )
        try:
            self.name = normalize_text(self.name)
            from invoices.services import validate_status
            validate_status(self, exclude_pk=self.pk)
        except InvoiceValidationError as e:
            logger.error(f"Validation failed for Status {self.name or 'Unnamed'}: {str(e)}")
            raise

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save invoice status with audit logging and atomic transaction."""
        logger.debug(f"Saving InvoiceStatus: {self.name or 'Unnamed'}, user={user}")
        if not skip_validation:
            self.clean()
        if self.is_locked and Status.objects.filter(pk=self.pk, is_locked=True).exists():
            raise InvalidInvoiceStatusError(
                message="Cannot modify a locked status.",
                code="cannot_modify_locked_status",
                details={"status_id": self.pk}
            )
        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user
        try:
            super().save(*args, **kwargs)
            logger.info(f"InvoiceStatus saved: {self.name} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save InvoiceStatus: {self.name or 'Unnamed'}, error: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to save invoice status: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete invoice status with atomic transaction."""
        logger.info(f"Soft deleting InvoiceStatus: {self.name}, user={user}")
        if self.is_locked:
            raise InvalidInvoiceStatusError(
                message="Cannot soft delete a locked status.",
                code="cannot_delete_locked_status",
                details={"status_id": self.id}
            )
        self.deleted_by = user
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.name}: deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.name}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to soft delete invoice status: {str(e)}",
                code="soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted invoice status with atomic transaction."""
        logger.info(f"Restoring InvoiceStatus: {self.name}, user={user}")
        if self.is_active:
            raise InvoiceValidationError(
                message="Cannot restore an active status.",
                code="already_active_status",
                details={"status_id": self.id}
            )
        try:
            self.is_active = True
            self.deleted_at = None
            self.updated_by = user
            self.save(user=user, skip_validation=False)  # Run validation to ensure no active duplicates
            logger.info(f"Successfully restored {self.name}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.name}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to restore invoice status: {str(e)}",
                code="restore_error",
                details={"error": str(e)}
            )

    def is_closed(self):
        """Return True if the status indicates the invoice is closed."""
        return self.code in ['PAID', 'CANCELLED']

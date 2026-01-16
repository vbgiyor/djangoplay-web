import logging

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import PAYMENT_REFERENCE_MAX_LENGTH, PAYMENT_STATUS_CODES
from invoices.exceptions import InvoiceValidationError
from invoices.services import update_invoice_status, validate_payment_amount, validate_payment_reference

logger = logging.getLogger(__name__)

class Payment(TimeStampedModel, AuditFieldsModel):

    """Model representing a payment made for an invoice."""

    id = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Invoice this payment is associated with."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount of the payment."
    )
    payment_date = models.DateField(
        default=timezone.now,
        help_text="Date when the payment was made."
    )
    payment_method = models.ForeignKey(
        'invoices.PaymentMethod',
        on_delete=models.PROTECT,
        help_text="Method used for the payment."
    )
    payment_reference = models.CharField(
        max_length=PAYMENT_REFERENCE_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="Reference for the payment (e.g., transaction ID)."
    )
    status = models.CharField(
        max_length=20,
        choices=[(k, v) for k, v in PAYMENT_STATUS_CODES.items()],
        default='PENDING',
        help_text="Status of the payment (e.g., PENDING, COMPLETED, FAILED)."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'payment'
        ordering = ['-payment_date', 'invoice']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        constraints = [
            models.UniqueConstraint(
                fields=['invoice', 'payment_reference'],
                condition=models.Q(deleted_at__isnull=True, payment_reference__isnull=False),
                name='unique_active_payment_reference'
            ),
        ]
        indexes = [
            models.Index(fields=['invoice', 'status'], name='payment_inv_status_idx'),
            models.Index(fields=['payment_date'], name='payment_paymentdate_idx'),
            GinIndex(fields=['payment_reference'], name='payment_ref_trgm_idx', opclasses=['gin_trgm_ops']),
            models.Index(fields=['invoice'], name='payment_invoice_idx'),
            models.Index(fields=['payment_method'], name='payment_method_idx'),
        ]

    def __str__(self):
        return f"Payment {self.payment_reference or self.id} for Invoice {self.invoice.invoice_number}"

    def clean(self):
        """Validate payment data, ensuring invoice and entity compatibility."""
        logger.debug(f"Validating Payment: {self.payment_reference or 'New Payment'}")

        if not hasattr(self, 'invoice') or self.invoice is None:
            raise InvoiceValidationError(
                message="An invoice must be associated with the payment.",
                code="invoice_error",
                details={"field": "invoice"}
            )

        try:
            logger.debug(f"Validating Payment for invoice {self.invoice.invoice_number}")
            # Normalize text fields
            if self.payment_reference:
                self.payment_reference = normalize_text(self.payment_reference)

            # Validate invoice entities
            if not self.invoice.issuer.is_active or not self.invoice.recipient.is_active:
                raise InvoiceValidationError(
                    message="Both issuer and recipient entities must be active.",
                    code="inactive_entity",
                    details={"invoice_id": self.invoice.id}
                )

            # Delegate validations to service layer
            validate_payment_amount(self.amount, self.invoice, self.pk)
            validate_payment_reference(self.payment_reference, self.payment_method.code, self.invoice, self.pk)

            # Validate payment date
            if self.payment_date < self.invoice.issue_date:
                raise InvoiceValidationError(
                    message="Payment date cannot be before invoice issue date.",
                    code="invalid_payment_date",
                    details={"field": "payment_date", "issue_date": self.invoice.issue_date, "payment_date": self.payment_date}
                )

            # Validate payment method
            if not self.payment_method.is_active:
                raise InvoiceValidationError(
                    message="Payment method must be active.",
                    code="inactive_payment_method",
                    details={"field": "payment_method", "method_code": self.payment_method.code}
                )

            super().clean()
        except Exception as e:
            logger.error(f"Validation error for payment {self.payment_reference or 'New Payment'}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Validation failed: {str(e)}",
                code="invoice_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save payment with audit logging and invoice status update."""
        logger.debug(f"Saving Payment: {self.payment_reference or 'New Payment'}, user={user}")
        if not skip_validation:
            self.clean()

        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user

        try:
            super().save(*args, **kwargs)
            update_invoice_status(self.invoice, user)
            logger.info(f"Payment saved successfully: {self} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save Payment: {self.payment_reference or 'New Payment'}, error: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to save payment: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete payment and update invoice status."""
        logger.info(f"Soft deleting Payment: {self.payment_reference or self.id}, user={user}")
        if not self.is_active:
            raise InvoiceValidationError(
                message="Cannot perform operation on an inactive payment.",
                code="inactive_payment",
                details={"payment_id": self.id, "status": self.status}
            )
        self.deleted_by = user
        try:
            super().soft_delete()
            update_invoice_status(self.invoice, user)
            logger.info(f"Successfully soft deleted {self.payment_reference or self.id}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.payment_reference or self.id}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to soft delete payment: {str(e)}",
                code="soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted payment and update invoice status."""
        logger.info(f"Restoring Payment: {self.payment_reference or self.id}, user={user}")
        try:
            super().restore()
            self.status = 'PENDING'
            self.updated_by = user
            self.save(user=user)
            update_invoice_status(self.invoice, user)
            logger.info(f"Successfully restored {self.payment_reference or self.id}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.payment_reference or self.id}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to restore payment: {str(e)}",
                code="restore_error",
                details={"error": str(e)}
            )

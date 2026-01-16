import logging
import re
from decimal import Decimal

from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from core.utils.redis_client import redis_client
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords

from invoices.constants import (
    DESCRIPTION_MAX_LENGTH,
    HSN_SAC_CODE_MAX_LENGTH,
    HSN_SAC_CODE_REGEX,
)
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.generic_gst_fields import GenericGSTFields
from invoices.services import calculate_line_item_total

logger = logging.getLogger(__name__)

class LineItem(GenericGSTFields, TimeStampedModel, AuditFieldsModel):

    """Model representing a line item in an invoice."""

    id = models.AutoField(primary_key=True)
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.CASCADE,
        related_name='line_items',
        help_text="Invoice this line item belongs to."
    )
    description = models.CharField(
        max_length=DESCRIPTION_MAX_LENGTH,
        help_text="Description of the line item (e.g., product or service name)."
    )
    hsn_sac_code = models.CharField(
        max_length=HSN_SAC_CODE_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="HSN or SAC code for the item (used for Indian GST compliance)."
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity of the item."
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price per unit of the item."
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Discount applied to this line item."
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount for this line item after taxes and discount."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'line_item'
        ordering = ['invoice', 'id']
        verbose_name = "Invoice Line Item"
        verbose_name_plural = "Invoice Line Items"
        constraints = [
            models.UniqueConstraint(
                fields=['invoice', 'description', 'hsn_sac_code'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_line_item'
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name='positive_quantity'
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name='non_negative_unit_price'
            ),
            models.CheckConstraint(
                check=models.Q(discount__gte=0),
                name='non_negative_discount'
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name='non_negative_total_amount'
            ),
        ]
        indexes = [
            GinIndex(fields=['description'], name='line_item_desc_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['hsn_sac_code'], name='line_item_hsn_sac_trgm_idx', opclasses=['gin_trgm_ops']),
            models.Index(fields=['invoice'], name='line_item_invoice_idx'),
            models.Index(fields=['hsn_sac_code'], name='line_item_hsn_sac_idx'),
        ]

    def __str__(self):
        return f"Line Item for {self.invoice.invoice_number}: {self.description}"

    # def clean(self):
    #     """Validate the line item data, ensuring compatibility with Entity relationships."""
    #     logger.debug(f"Validating LineItem: {self.description}")
    #     logger.debug(f"Preparing to save LineItem: {self.description or 'New Line Item'}, invoice_id={self.invoice_id}")
    #     from invoices.services.line_item import get_safe_decimal  # Import get_safe_decimal
    #     try:
    #         # Validate HSN/SAC code
    #         if self.hsn_sac_code and not re.match(HSN_SAC_CODE_REGEX, self.hsn_sac_code):
    #             raise InvoiceValidationError(
    #                 message=f"HSN/SAC code must match pattern {HSN_SAC_CODE_REGEX}.",
    #                 code="invalid_hsn_sac_code",
    #                 details={"field": "hsn_sac_code", "value": self.hsn_sac_code}
    #             )

    #         # Validate quantities and amounts
    #         if self.quantity <= 0:
    #             raise InvoiceValidationError(
    #                 message="Quantity must be positive.",
    #                 code="invalid_quantity",
    #                 details={"field": "quantity", "value": self.quantity}
    #             )
    #         if self.unit_price < 0:
    #             raise InvoiceValidationError(
    #                 message="Unit price cannot be negative.",
    #                 code="invalid_unit_price",
    #                 details={"field": "unit_price", "value": self.unit_price}
    #             )
    #         discount = get_safe_decimal(self.discount)  # Use get_safe_decimal to handle None
    #         if discount < 0:
    #             raise InvoiceValidationError(
    #                 message="Discount cannot be negative.",
    #                 code="invalid_discount",
    #                 details={"field": "discount", "value": str(self.discount)}
    #             )

    #         # Validate invoice
    #         if not self.invoice.is_active:
    #             raise InvoiceValidationError(
    #                 message="Invoice must be active.",
    #                 code="inactive_invoice",
    #                 details={"field": "invoice", "invoice_id": self.invoice.id}
    #             )

    #         # Calculate base amount for validation
    #         base_amount = self.quantity * self.unit_price - discount  # Use the safe discount

    #         # Validate tax fields using GenericTaxModel
    #         self.clean_tax_fields(
    #             has_gst_required_fields=self.invoice.has_gst_required_fields,
    #             billing_region_id=self.invoice.billing_region.id if self.invoice.billing_region else None,
    #             billing_country=self.invoice.billing_country,
    #             issue_date=self.invoice.issue_date,
    #             tax_exemption_status=self.invoice.tax_exemption_status,
    #             base_amount=base_amount
    #         )

    #         # Validate GST rates match invoice
    #         if self.invoice.has_gst_required_fields and self.invoice.tax_exemption_status == 'NONE':
    #             if self.cgst_rate != self.invoice.cgst_rate:
    #                 raise GSTValidationError(
    #                     message="CGST rate must match invoice CGST rate.",
    #                     code="inconsistent_gst_rates",
    #                     details={"field": "cgst_rate", "invoice_rate": str(self.invoice.cgst_rate)}
    #                 )
    #             if self.sgst_rate != self.invoice.sgst_rate:
    #                 raise GSTValidationError(
    #                     message="SGST rate must match invoice SGST rate.",
    #                     code="inconsistent_gst_rates",
    #                     details={"field": "sgst_rate", "invoice_rate": str(self.invoice.sgst_rate)}
    #                 )
    #             if self.igst_rate != self.invoice.igst_rate:
    #                 raise GSTValidationError(
    #                     message="IGST rate must match invoice IGST rate.",
    #                     code="inconsistent_gst_rates",
    #                     details={"field": "igst_rate", "invoice_rate": str(self.invoice.igst_rate)}
    #                 )

    #         # Validate total_amount consistency
    #         if self.total_amount is not None:
    #             cgst_amount = get_safe_decimal(self.cgst_amount)  # Normalize cgst_amount
    #             sgst_amount = get_safe_decimal(self.sgst_amount)  # Normalize sgst_amount
    #             igst_amount = get_safe_decimal(self.igst_amount)  # Normalize igst_amount
    #             expected_total = (base_amount + cgst_amount + sgst_amount + igst_amount).quantize(Decimal('0.01'))
    #             normalized_total_amount = get_safe_decimal(self.total_amount).quantize(Decimal('0.01'))
    #             if normalized_total_amount != expected_total:
    #                 raise InvoiceValidationError(
    #                     f"Total amount {normalized_total_amount} does not match expected {expected_total} (base + GST amounts).",
    #                     code="invalid_total_amount",
    #                     details={"field": "total_amount", "expected": str(expected_total)}
    #                 )

    #         super().clean()
    #     except Exception as e:
    #         logger.error(f"Validation error for line item {self.id or 'New Line Item'}: {str(e)}", exc_info=True)
    #         raise InvoiceValidationError(
    #             message=f"Validation failed: {str(e)}",
    #             code="invoice_error",
    #             details={"error": str(e)}
    #         )

    def clean(self):
        """Validate the line item data, ensuring compatibility with Entity relationships."""
        logger.debug(f"Validating LineItem: {self.description}")
        logger.debug(f"Preparing to save LineItem: {self.description or 'New Line Item'}, invoice_id={self.invoice_id}")
        from invoices.services.line_item import get_safe_decimal  # Import get_safe_decimal
        try:
            # Validate HSN/SAC code
            if self.hsn_sac_code and not re.match(HSN_SAC_CODE_REGEX, self.hsn_sac_code):
                raise InvoiceValidationError(
                    message=f"HSN/SAC code must match pattern {HSN_SAC_CODE_REGEX}.",
                    code="invalid_hsn_sac_code",
                    details={"field": "hsn_sac_code", "value": self.hsn_sac_code}
                )

            # Validate quantities and amounts
            if self.quantity <= 0:
                raise InvoiceValidationError(
                    message="Quantity must be positive.",
                    code="invalid_quantity",
                    details={"field": "quantity", "value": self.quantity}
                )
            if self.unit_price < 0:
                raise InvoiceValidationError(
                    message="Unit price cannot be negative.",
                    code="invalid_unit_price",
                    details={"field": "unit_price", "value": self.unit_price}
                )
            discount = get_safe_decimal(self.discount)  # Use get_safe_decimal to handle None
            if discount < 0:
                raise InvoiceValidationError(
                    message="Discount cannot be negative.",
                    code="invalid_discount",
                    details={"field": "discount", "value": str(self.discount)}
                )

            # Validate invoice
            if not self.invoice.is_active:
                raise InvoiceValidationError(
                    message="Invoice must be active.",
                    code="inactive_invoice",
                    details={"field": "invoice", "invoice_id": self.invoice.id}
                )

            # Synchronize GST rates with invoice
            if self.invoice and self.invoice.has_gst_required_fields:
                self.cgst_rate = self.invoice.cgst_rate
                self.sgst_rate = self.invoice.sgst_rate
                self.igst_rate = self.invoice.igst_rate

            # Calculate base amount for validation
            base_amount = self.quantity * self.unit_price - discount

            # Validate tax fields using GenericTaxModel
            self.clean_tax_fields(
                has_gst_required_fields=self.invoice.has_gst_required_fields,
                billing_region_id=self.invoice.billing_region.id if self.invoice.billing_region else None,
                billing_country=self.invoice.billing_country,
                issue_date=self.invoice.issue_date,
                tax_exemption_status=self.invoice.tax_exemption_status,
                base_amount=base_amount
            )

            # Validate GST rates match invoice
            if self.invoice.has_gst_required_fields and self.invoice.tax_exemption_status == 'NONE':
                if self.cgst_rate != self.invoice.cgst_rate:
                    raise GSTValidationError(
                        message="CGST rate must match invoice CGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "cgst_rate", "invoice_rate": str(self.invoice.cgst_rate)}
                    )
                if self.sgst_rate != self.invoice.sgst_rate:
                    raise GSTValidationError(
                        message="SGST rate must match invoice SGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "sgst_rate", "invoice_rate": str(self.invoice.sgst_rate)}
                    )
                if self.igst_rate != self.invoice.igst_rate:
                    raise GSTValidationError(
                        message="IGST rate must match invoice IGST rate.",
                        code="inconsistent_gst_rates",
                        details={"field": "igst_rate", "invoice_rate": str(self.invoice.igst_rate)}
                    )

            # Recalculate total and GST amounts before validation
            total_data = calculate_line_item_total(self)
            self.total_amount = total_data['total']
            self.cgst_amount = total_data.get('cgst_amount', Decimal('0.00'))
            self.sgst_amount = total_data.get('sgst_amount', Decimal('0.00'))
            self.igst_amount = total_data.get('igst_amount', Decimal('0.00'))

            # Validate total_amount consistency
            cgst_amount = get_safe_decimal(self.cgst_amount)
            sgst_amount = get_safe_decimal(self.sgst_amount)
            igst_amount = get_safe_decimal(self.igst_amount)
            expected_total = (base_amount + cgst_amount + sgst_amount + igst_amount).quantize(Decimal('0.01'))
            normalized_total_amount = get_safe_decimal(self.total_amount).quantize(Decimal('0.01'))
            if normalized_total_amount != expected_total:
                raise InvoiceValidationError(
                    f"Total amount {normalized_total_amount} does not match expected {expected_total} (base + GST amounts).",
                    code="invalid_total_amount",
                    details={"field": "total_amount", "expected": str(expected_total)}
                )

            super().clean()
        except Exception as e:
            logger.error(f"Validation error for line item {self.id or 'New Line Item'}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Validation failed: {str(e)}",
                code="invoice_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def save(self, *args, user=None, skip_validation=False, **kwargs):
        """Save line item with audit logging, service layer integration, and atomic transaction."""
        logger.debug(f"Saving InvoiceLineItem: {self.description or 'New Line Item'}, user={user}")
        if not skip_validation:
            self.clean()

         # Synchronize GST rates with invoice before calculating totals
        if self.invoice and self.invoice.has_gst_required_fields:
            self.cgst_rate = self.invoice.cgst_rate
            self.sgst_rate = self.invoice.sgst_rate
            self.igst_rate = self.invoice.igst_rate
            # Invalidate cache to ensure fresh calculations
            cache_key = f"line_item:{self.id or 'new'}:total"
            redis_client.delete(cache_key)
            logger.debug(f"Invalidated cache for LineItem: {cache_key}")
            logger.debug(f"Passed Rates: {self.cgst_rate},{self.sgst_rate},{self.igst_rate}")

        # Calculate total amount and GST amounts using service layer
        try:
            total_data = calculate_line_item_total(self)
            self.total_amount = total_data['total']
            self.cgst_amount = total_data.get('cgst_amount', Decimal('0.00'))
            self.sgst_amount = total_data.get('sgst_amount', Decimal('0.00'))
            self.igst_amount = total_data.get('igst_amount', Decimal('0.00'))
            logger.debug(f"Passed amount: {self.cgst_amount},{self.sgst_amount},{self.igst_amount}")

        except Exception as e:
            logger.error(f"Failed to calculate total for line item {self.description or 'New Line Item'}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                message=f"Failed to calculate line item total: {str(e)}",
                code="total_calculation_failed",
                details={"error": str(e)}
            )

        User = get_user_model()
        if user and isinstance(user, User):
            if not self.pk:
                self.created_by = user
            self.updated_by = user

        try:
            super().save(*args, **kwargs)
            logger.info(f"InvoiceLineItem saved successfully: {self} (ID: {self.pk})")
        except Exception as e:
            logger.error(f"Failed to save InvoiceLineItem: {self.description or 'New Line Item'}, error: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to save line item: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
        return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete line item with atomic transaction."""
        logger.info(f"Soft deleting InvoiceLineItem: {self.description}, user={user}")
        if not self.is_active:
            raise InvoiceValidationError(
                message="Cannot perform operation on an inactive line item.",
                code="inactive_line_item",
                details={"line_item_id": self.pk}
            )
        self.deleted_by = user
        self.is_active = False
        self.deleted_at = timezone.now()
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.description}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to soft delete line item: {str(e)}",
                code="line_item_soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted line item with atomic transaction."""
        logger.info(f"Restoring InvoiceLineItem: {self.description}, user={user}")
        if self.is_active:
            raise InvoiceValidationError(
                message="Cannot restore an active line item.",
                code="already_active_line_item",
                details={"line_item_id": self.pk}
            )
        self.deleted_by = None
        self.is_active = True
        self.deleted_at = None
        try:
            super().restore()
            self.updated_by = user
            self.save(user=user)
            logger.info(f"Successfully restored {self.description}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.description}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to restore line item: {str(e)}",
                code="line_item_restore_error",
                details={"error": str(e)}
            )

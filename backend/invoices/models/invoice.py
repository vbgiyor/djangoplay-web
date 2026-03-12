import logging
from decimal import Decimal

import redis
from core.models import ActiveManager, AuditFieldsModel, TimeStampedModel
from core.utils.redis_client import redis_client
from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from entities.models import Entity
from locations.models import CustomCountry, CustomRegion
from simple_history.models import HistoricalRecords
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import (
    DESCRIPTION_MAX_LENGTH,
    GSTIN_MAX_LENGTH,
    INVOICE_NUMBER_MAX_LENGTH,
    PAYMENT_METHOD_CODES,
    PAYMENT_REFERENCE_MAX_LENGTH,
    PAYMENT_TERMS_CHOICES,
    TAX_EXEMPTION_CHOICES,
)
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.generic_gst_fields import GenericGSTFields
from invoices.models.status import Status
from invoices.services.invoice import calculate_total_amount

logger = logging.getLogger(__name__)

class Invoice(GenericGSTFields, TimeStampedModel, AuditFieldsModel):

    """Model representing an invoice for billing and tax operations."""

    def get_default_status_id():
        from django.db import connection
        if 'invoices_status' not in connection.introspection.table_names():
            return None
        status, created = Status.objects.get_or_create(
            code='DRAFT',
            defaults={'name': 'Draft', 'is_active': True}
        )
        return status.id

    id = models.AutoField(primary_key=True)
    invoice_number = models.CharField(
        max_length=INVOICE_NUMBER_MAX_LENGTH,
        unique=True,
        help_text="Unique invoice number."
    )
    description = models.CharField(
        max_length=DESCRIPTION_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="Optional description of the invoice."
    )
    issuer = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name='invoices_issued',
        help_text="Entity issuing the invoice."
    )
    recipient = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name='invoices_received',
        help_text="Entity receiving the invoice."
    )
    billing_address = models.ForeignKey(
        'fincore.Address',
        on_delete=models.PROTECT,
        help_text="Billing address for the invoice."
    )
    billing_country = models.ForeignKey(
        CustomCountry,
        on_delete=models.PROTECT,
        help_text="Country associated with the billing address."
    )
    billing_region = models.ForeignKey(
        CustomRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Region or state associated with the billing address."
    )
    issue_date = models.DateField(
        default=timezone.now,
        blank=True,
        null=True,
        help_text="Date when the invoice was issued."
    )
    due_date = models.DateField(
        help_text="Date when the invoice payment is due."
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name='invoices',
        default=get_default_status_id,
        help_text="Status of the invoice."
    )
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default="NET_30",
        blank=True,
        help_text="Payment terms for the invoice."
    )
    currency = models.CharField(
        max_length=3,
        default="INR",
        blank=True,
        help_text="Currency of the invoice."
    )
    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Base amount of the invoice before taxes."
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount including taxes."
    )
    tax_exemption_status = models.CharField(
        max_length=20,
        choices=TAX_EXEMPTION_CHOICES,
        default="NONE",
        blank=True,           # <-- added
        help_text="Tax exemption status of the invoice."
    )

    payment_method = models.CharField(
        max_length=20,
        choices=[(k, v) for k, v in PAYMENT_METHOD_CODES.items()],
        null=True,
        blank=True,
        help_text="Payment method used (e.g., UPI, CREDIT_CARD)."
    )
    payment_reference = models.CharField(
        max_length=PAYMENT_REFERENCE_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="Reference for the payment (e.g., transaction ID)."
    )
    issuer_gstin = models.CharField(
        max_length=GSTIN_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="GSTIN of the issuer (for Indian invoices)."
    )
    recipient_gstin = models.CharField(
        max_length=GSTIN_MAX_LENGTH,
        blank=True,
        null=True,
        help_text="GSTIN of the recipient (for Indian invoices)."
    )
    history = HistoricalRecords()

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'invoice'
        ordering = ['-issue_date', 'invoice_number']
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        constraints = [
            models.UniqueConstraint(
                fields=['issuer', 'invoice_number'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_invoice_number'
            ),
        ]
        indexes = [
            models.Index(fields=['issuer', 'recipient'], name='inv_issuer_recpt_idx'),
            models.Index(fields=['issue_date', 'due_date'], name='invoice_dates_idx'),
            models.Index(fields=['created_by', 'updated_by'], name='invoice_auditby_idx'),
            GinIndex(fields=['invoice_number'], name='invoice_number_trgm_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['description'], name='invoice_desc_trgm_idx', opclasses=['gin_trgm_ops']),
            models.Index(fields=['issuer'], name='invoice_issuer_idx'),
            models.Index(fields=['recipient'], name='invoice_recipient_idx'),
            models.Index(fields=['billing_address'], name='invoice_billing_address_idx'),
            models.Index(fields=['billing_country'], name='invoice_billing_country_idx'),
            models.Index(fields=['billing_region'], name='invoice_billing_region_idx'),
            models.Index(fields=['status'], name='invoice_status_idx'),
            models.Index(fields=['invoice_number'], name='invoice_number_idx'),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} from {self.issuer.name} to {self.recipient.name}"

    @property
    def has_gst_required_fields(self):
        """Check if the invoice requires GST processing based on the billing country."""
        return self.billing_country and self.billing_country.country_code.upper() == 'IN'


    def clean(self):
        """Validate invoice fields, integrating with Entity's new relationships."""
        logger.debug(f"Validating Invoice: {self.invoice_number}")

        if isinstance(self.base_amount, str):
            try:
                self.base_amount = Decimal(self.base_amount)
            except Exception:
                raise InvoiceValidationError(
                "Invalid value for {base_amount}.",
                code="invalid_base_amount",
                details={"field": "base_amount", "value": self.base_amount}
            )

        # Normalize text fields
        for field in ['invoice_number', 'payment_reference', 'description', 'issuer_gstin', 'recipient_gstin']:
            value = getattr(self, field, None)
            if value:
                setattr(self, field, normalize_text(value))

        # Validate issuer and recipient
        if not self.issuer.is_active:
            raise InvoiceValidationError(
                "Issuer must be an active entity.",
                code="inactive_issuer",
                details={"field": "issuer", "entity_id": self.issuer.id}
            )
        if not self.recipient.is_active:
            raise InvoiceValidationError(
                "Recipient must be an active entity.",
                code="inactive_recipient",
                details={"field": "recipient", "entity_id": self.recipient.id}
            )

        # Validate billing address
        recipient_mapping = self.recipient.get_entity_mapping()
        if self.billing_address.entity_mapping != recipient_mapping:
            raise InvoiceValidationError(
                "Billing address must belong to the recipient entity.",
                code="invalid_billing_address",
                details={"field": "billing_address", "address_id": self.billing_address.id}
            )

        # Validate billing country and region
        if self.billing_address.city.subregion.region.country != self.billing_country:
            raise InvoiceValidationError(
                "Billing country must match the address's country.",
                code="invalid_billing_country",
                details={"field": "billing_country", "country_id": self.billing_country.id}
            )
        if self.billing_region and self.billing_region.country != self.billing_country:
            raise InvoiceValidationError(
                "Billing region must belong to the billing country.",
                code="invalid_billing_region",
                details={"field": "billing_region", "region_id": self.billing_region.id}
            )

        # Validate GST-related fields
        if self.has_gst_required_fields:
            from utilities.utils.entities.entity_validations import validate_gstin

            # Defensive check for issuer's region
            issuer_region = self.issuer.default_address.city.subregion.region if self.issuer.default_address and self.issuer.default_address.city else None

            if self.issuer_gstin:
                try:
                    validate_gstin(self.issuer_gstin)
                except ValidationError as e:
                    raise GSTValidationError(
                        f"Invalid issuer GSTIN: {str(e)}",
                        code="invalid_issuer_gstin",
                        details={"field": "issuer_gstin", "value": self.issuer_gstin}
                    )
                issuer_tax_profile = self.issuer.get_tax_profiles().filter(
                    tax_identifier_type='GSTIN',
                    tax_identifier=self.issuer_gstin
                ).first()
                if not issuer_tax_profile:
                    raise GSTValidationError(
                        "Issuer GSTIN does not match any tax profile for the issuer.",
                        code="invalid_issuer_gstin",
                        details={"field": "issuer_gstin", "value": self.issuer_gstin}
                    )
                issuer_state_code = self.issuer_gstin[:2]
                if issuer_region and issuer_state_code != issuer_region.code:
                    raise GSTValidationError(
                        f"Issuer GSTIN state code {issuer_state_code} does not match issuer's address state code {issuer_region.code}.",
                        code="issuer_gstin_state_mismatch",
                        details={"field": "issuer_gstin", "gstin": self.issuer_gstin, "state_code": issuer_region.code}
                    )

            if self.recipient_gstin:
                try:
                    validate_gstin(self.recipient_gstin)
                except ValidationError as e:
                    raise GSTValidationError(
                        f"Invalid recipient GSTIN: {str(e)}",
                        code="invalid_recipient_gstin",
                        details={"field": "recipient_gstin", "value": self.recipient_gstin}
                    )
                recipient_tax_profile = self.recipient.get_tax_profiles().filter(
                    tax_identifier_type='GSTIN',
                    tax_identifier=self.recipient_gstin
                ).first()
                if not recipient_tax_profile:
                    raise GSTValidationError(
                        "Recipient GSTIN does not match any tax profile for the recipient.",
                        code="invalid_recipient_gstin",
                        details={"field": "recipient_gstin", "value": self.recipient_gstin}
                    )
                recipient_state_code = self.recipient_gstin[:2]
                # Defensive check for recipient's region
                recipient_region = self.billing_address.city.subregion.region if self.billing_address and self.billing_address.city else None
                if recipient_region and recipient_state_code != recipient_region.code:
                    raise GSTValidationError(
                        f"Recipient GSTIN state code {recipient_state_code} does not match billing address state code {recipient_region.code}.",
                        code="recipient_gstin_state_mismatch",
                        details={"field": "recipient_gstin", "gstin": self.recipient_gstin, "state_code": recipient_region.code}
                    )

        # Validate tax fields using GenericTaxModel
        self.clean_tax_fields(
            has_gst_required_fields=self.has_gst_required_fields,
            billing_region_id=self.billing_region.id if self.billing_region else None,
            billing_country=self.billing_country,
            issue_date=self.issue_date,
            tax_exemption_status=self.tax_exemption_status,
            base_amount=self.base_amount
        )

        # Validate amounts
        if self.base_amount < 0:
            raise InvoiceValidationError(
                "Base amount cannot be negative.",
                code="invalid_base_amount",
                details={"field": "base_amount", "value": str(self.base_amount)}
            )

        # Validate dates
        if self.due_date < self.issue_date:
            raise InvoiceValidationError(
                "Due date cannot be before issue date.",
                code="invalid_due_date",
                details={"field": "due_date", "issue_date": self.issue_date, "due_date": self.due_date}
            )

        # Validate status
        if not self.status.is_active or self.status.deleted_at is not None:
            raise InvoiceValidationError(
                "Invoice status must be active.",
                code="inactive_status",
                details={"field": "status", "status_id": self.status.id}
            )

        super().clean()

    @transaction.atomic
    def save(self, user=None, skip_validation=False, *args, **kwargs):
        """
        Save the invoice instance, performing validation and updating totals.
        Also update related LineItem instances' GST rates and totals.
        """
        with transaction.atomic():
            # Set skip_validation flag for signal handler
            self._skip_validation = skip_validation

            # Perform validation unless skipped
            if not skip_validation:
                self.clean()

            # Store original GST rates for comparison
            original_cgst_rate = self.cgst_rate
            original_sgst_rate = self.sgst_rate
            original_igst_rate = self.igst_rate
            if self.pk:
                try:
                    original_invoice = Invoice.objects.get(pk=self.pk)
                    original_cgst_rate = original_invoice.cgst_rate
                    original_sgst_rate = original_invoice.sgst_rate
                    original_igst_rate = original_invoice.igst_rate
                except Invoice.DoesNotExist:
                    pass

            # Invalidate invoice total cache to ensure fresh calculation
            cache_key = f"invoice:{self.id or 'new'}:total_amount"
            try:
                redis_client.delete(cache_key)
                logger.debug(f"Invalidated cache for Invoice: {cache_key}")
            except redis.RedisError as e:
                logger.warning(f"Failed to invalidate cache for {cache_key}: {str(e)}")

            # Save the invoice to the database to assign a primary key
            super().save(*args, **kwargs)

            # Update related LineItem instances if GST rates have changed
            from invoices.services import calculate_line_item_total
            if (self.cgst_rate != original_cgst_rate or
                self.sgst_rate != original_sgst_rate or
                self.igst_rate != original_igst_rate):
                line_items = self.line_items.filter(is_active=True, deleted_at__isnull=True)
                for line_item in line_items:
                    line_item.cgst_rate = self.cgst_rate
                    line_item.sgst_rate = self.sgst_rate
                    line_item.igst_rate = self.igst_rate
                    # Invalidate line item cache
                    cache_key_line = f"line_item:{line_item.id}:total"
                    try:
                        redis_client.delete(cache_key_line)
                        logger.debug(f"Invalidated cache for LineItem: {cache_key_line}")
                    except redis.RedisError as e:
                        logger.warning(f"Failed to invalidate cache for {cache_key_line}: {str(e)}")
                    # Recalculate totals for the LineItem
                    total_data = calculate_line_item_total(line_item)
                    line_item.total_amount = total_data['total'].quantize(Decimal('0.01'))
                    line_item.cgst_amount = total_data.get('cgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                    line_item.sgst_amount = total_data.get('sgst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                    line_item.igst_amount = total_data.get('igst_amount', Decimal('0.00')).quantize(Decimal('0.01'))
                    try:
                        line_item.save(user=user, skip_validation=True)
                        logger.info(f"Updated LineItem {line_item.id} for Invoice {self.invoice_number} with new GST rates and totals")
                    except Exception as e:
                        logger.error(f"Failed to update LineItem {line_item.id} for Invoice {self.invoice_number}: {str(e)}", exc_info=True)
                        raise InvoiceValidationError(
                            message=f"Failed to update LineItem {line_item.id}: {str(e)}",
                            code="line_item_update_error",
                            details={"error": str(e)}
                        )

            # Calculate and update invoice totals
            try:
                total_data = calculate_total_amount(self)
                self.base_amount = total_data.get('base', Decimal('0.00')).quantize(Decimal('0.01'))
                self.cgst_amount = total_data.get('cgst', Decimal('0.00')).quantize(Decimal('0.01'))
                self.sgst_amount = total_data.get('sgst', Decimal('0.00')).quantize(Decimal('0.01'))
                self.igst_amount = total_data.get('igst', Decimal('0.00')).quantize(Decimal('0.01'))
                self.total_amount = total_data.get('total', Decimal('0.00')).quantize(Decimal('0.01'))

                User = get_user_model()
                if user and isinstance(user, User):
                    if not self.pk:
                        self.created_by = user
                    self.updated_by = user

                # Save again to update the total fields
                super().save(*args, **kwargs)
                logger.info(f"Invoice saved successfully: {self} (ID: {self.pk})")
            except InvoiceValidationError as e:
                logger.error(f"Failed to calculate or update total for invoice {self.invoice_number}: {str(e)}", exc_info=True)
                raise
            return self

    @transaction.atomic
    def soft_delete(self, user=None):
        """Soft delete invoice and update status."""
        logger.info(f"Soft deleting Invoice: {self.invoice_number}, user={user}")
        if not self.is_active:
            raise InvoiceValidationError(
                "Cannot perform operation on an inactive invoice.",
                code="inactive_invoice",
                details={"invoice_id": self.pk, "status": self.status.code}
            )
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.status = Status.objects.get(code='CANCELLED', is_active=True, deleted_at__isnull=True)
        self.is_active = False
        try:
            super().soft_delete()
            logger.info(f"Successfully soft deleted {self.invoice_number}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to soft delete {self.invoice_number}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to soft delete invoice: {str(e)}",
                code="invoice_soft_delete_error",
                details={"error": str(e)}
            )

    @transaction.atomic
    def restore(self, user=None):
        """Restore a soft-deleted invoice."""
        logger.info(f"Restoring Invoice: {self.invoice_number}, user={user}")
        self.deleted_at = None
        self.deleted_by = None
        self.status = Status.objects.get(code='DRAFT', is_active=True, deleted_at__isnull=True)
        self.is_active = True
        try:
            super().restore()
            logger.info(f"Successfully restored {self.invoice_number}: is_active={self.is_active}, deleted_at={self.deleted_at}")
        except Exception as e:
            logger.error(f"Failed to restore {self.invoice_number}: {str(e)}", exc_info=True)
            raise InvoiceValidationError(
                f"Failed to restore invoice: {str(e)}",
                code="invoice_restore_error",
                details={"error": str(e)}
            )

import logging
from decimal import Decimal

from django.db import models

from invoices.exceptions import GSTValidationError

logger = logging.getLogger(__name__)

class GenericGSTFields(models.Model):

    """Abstract model for common GST-related fields and validation."""

    cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Central GST rate (if applicable)."
    )
    sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="State GST rate (if applicable)."
    )
    igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Integrated GST rate (if applicable)."
    )
    cgst_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="CGST amount"
    )
    sgst_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="SGST amount"
    )
    igst_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="IGST amount"
    )

    class Meta:
        abstract = True



    def clean_tax_fields(self, has_gst_required_fields, billing_region_id, billing_country, issue_date, tax_exemption_status, base_amount):
        from invoices.services.gst_configuration import is_interstate_transaction, validate_gst_rates
        from invoices.services.line_item import get_safe_decimal
        try:
            if billing_country and billing_country.country_code.upper() == 'IN' and has_gst_required_fields and tax_exemption_status not in ['EXEMPT', 'ZERO_RATED']:
                try:
                    validate_gst_rates(
                        cgst_rate=self.cgst_rate,
                        sgst_rate=self.sgst_rate,
                        igst_rate=self.igst_rate,
                        region_id=billing_region_id,
                        country_id=billing_country.id,
                        issue_date=issue_date,
                        tax_exemption_status=tax_exemption_status
                    )
                except GSTValidationError as e:
                    raise GSTValidationError(str(e))

                # is_inter_state = is_interstate_transaction(
                #     seller_gstin=getattr(self, 'issuer_gstin', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'issuer_gstin', None),
                #     buyer_gstin=getattr(self, 'recipient_gstin', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'recipient_gstin', None),
                #     billing_region_id=billing_region_id,
                #     billing_country_id=billing_country.id,
                #     issuer=getattr(self, 'issuer', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'issuer', None),
                #     recipient=getattr(self, 'recipient', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'recipient', None),
                #     issue_date=issue_date
                # )
                # Skip interstate check for GSTConfiguration, as it's handled in GSTConfiguration.clean
                from invoices.models.gst_configuration import GSTConfiguration
                if isinstance(self, GSTConfiguration):
                    is_inter_state = not billing_region_id  # Interstate if no region specified
                else:
                    is_inter_state = is_interstate_transaction(
                        seller_gstin=getattr(self, 'issuer_gstin', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'issuer_gstin', None),
                        buyer_gstin=getattr(self, 'recipient_gstin', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'recipient_gstin', None),
                        billing_region_id=billing_region_id,
                        billing_country_id=billing_country.id,
                        issuer=getattr(self, 'issuer', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'issuer', None),
                        recipient=getattr(self, 'recipient', None) or getattr(self, 'invoice', None) and getattr(self.invoice, 'recipient', None),
                        issue_date=issue_date
                    )

                cgst_amount = get_safe_decimal(self.cgst_amount)
                sgst_amount = get_safe_decimal(self.sgst_amount)
                igst_amount = get_safe_decimal(self.igst_amount)

                if is_inter_state:
                    if igst_amount != (base_amount * get_safe_decimal(self.igst_rate) / Decimal('100')).quantize(Decimal('0.01')):
                        raise GSTValidationError(
                            message=f"IGST amount {igst_amount} does not match expected {(base_amount * get_safe_decimal(self.igst_rate) / Decimal('100')).quantize(Decimal('0.01'))}.",
                            code="invalid_igst_amount",
                            details={"field": "igst_amount"}
                        )
                    if cgst_amount != Decimal('0.00'):
                        raise GSTValidationError(
                            message="CGST amount must be zero for interstate transactions.",
                            code="invalid_cgst_amount",
                            details={"field": "cgst_amount"}
                        )
                    if sgst_amount != Decimal('0.00'):
                        raise GSTValidationError(
                            message="SGST amount must be zero for interstate transactions.",
                            code="invalid_sgst_amount",
                            details={"field": "sgst_amount"}
                        )
                else:
                    if self.cgst_rate is not None and self.sgst_rate is not None:
                        expected_cgst = (base_amount * get_safe_decimal(self.cgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                        expected_sgst = (base_amount * get_safe_decimal(self.sgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                        self.cgst_amount = expected_cgst
                        self.sgst_amount = expected_sgst
                        if cgst_amount != expected_cgst:
                            logger.warning(f"Corrected CGST amount from {cgst_amount} to {expected_cgst} for intrastate transaction")
                        if sgst_amount != expected_sgst:
                            logger.warning(f"Corrected SGST amount from {sgst_amount} to {expected_sgst} for intrastate transaction")
                    else:
                        self.cgst_amount = Decimal('0.00')
                        self.sgst_amount = Decimal('0.00')
                    if igst_amount != Decimal('0.00'):
                        raise GSTValidationError(
                            message="IGST amount must be zero for intrastate transactions.",
                            code="invalid_igst_amount",
                            details={"field": "igst_amount"}
                        )
        except GSTValidationError as e:
            raise GSTValidationError(f"Failed to validate GST fields: {str(e)}")

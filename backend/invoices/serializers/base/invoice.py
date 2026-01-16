import logging

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.invoice import Invoice
from invoices.services import validate_gst_rates, validate_invoice

logger = logging.getLogger(__name__)


class BaseInvoiceSerializer(serializers.ModelSerializer):

    """
    Version-agnostic base serializer for Invoice.
    Business rules live here.
    """

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("id", "total_amount")

    def validate(self, data):
        try:
            for field in [
                "invoice_number",
                "description",
                "payment_reference",
                "issuer_gstin",
                "recipient_gstin",
            ]:
                if field in data and data[field]:
                    data[field] = normalize_text(data[field])

            invoice = Invoice(**data)

            validate_invoice(
                invoice,
                exclude_pk=self.instance.pk if self.instance else None,
            )

            if data.get("issuer_gstin") and data.get("recipient_gstin"):
                validate_gst_rates(
                    cgst_rate=data.get("cgst_rate"),
                    sgst_rate=data.get("sgst_rate"),
                    igst_rate=data.get("igst_rate"),
                    region_id=data.get("billing_region").id if data.get("billing_region") else None,
                    country_id=data.get("billing_country").id if data.get("billing_country") else None,
                    issue_date=data.get("issue_date"),
                    tax_exemption_status=data.get("tax_exemption_status"),
                    hsn_sac_code=None,
                )

            return data

        except (InvoiceValidationError, GSTValidationError):
            raise
        except Exception as e:
            logger.exception("Invoice validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="invoice_validation_error",
            )

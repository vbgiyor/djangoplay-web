import logging

from django.db import transaction

from invoices.exceptions import InvoiceValidationError
from invoices.models.invoice import Invoice
from invoices.serializers.base import BaseInvoiceSerializer
from invoices.services import calculate_total_amount, generate_invoice_number

logger = logging.getLogger(__name__)


class InvoiceWriteSerializer(BaseInvoiceSerializer):

    """
    Write-capable serializer for Invoice (POST / PUT / PATCH).
    """

    class Meta(BaseInvoiceSerializer.Meta):
        read_only_fields = (
            "id",
            "total_amount",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
        )

    @transaction.atomic
    def create(self, validated_data):
        try:
            if not validated_data.get("invoice_number"):
                validated_data["invoice_number"] = generate_invoice_number()

            invoice = Invoice.objects.create(**validated_data)

            totals = calculate_total_amount(invoice)
            invoice.base_amount = totals.get("base", invoice.base_amount)
            invoice.cgst_amount = totals.get("cgst", 0)
            invoice.sgst_amount = totals.get("sgst", 0)
            invoice.igst_amount = totals.get("igst", 0)
            invoice.total_amount = totals.get("total")

            invoice.save()
            return invoice

        except Exception as e:
            logger.exception("Invoice creation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="invoice_create_failed",
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            totals = calculate_total_amount(instance)
            instance.base_amount = totals.get("base", instance.base_amount)
            instance.cgst_amount = totals.get("cgst", 0)
            instance.sgst_amount = totals.get("sgst", 0)
            instance.igst_amount = totals.get("igst", 0)
            instance.total_amount = totals.get("total")

            instance.save()
            return instance

        except Exception as e:
            logger.exception("Invoice update failed")
            raise InvoiceValidationError(
                message=str(e),
                code="invoice_update_failed",
            )

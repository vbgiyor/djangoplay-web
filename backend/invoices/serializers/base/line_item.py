import logging
from decimal import Decimal

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.line_item import LineItem
from invoices.services.line_item import calculate_line_item_total, validate_line_item

logger = logging.getLogger(__name__)


class BaseLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = "__all__"
        read_only_fields = (
            "id",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        )

    def validate(self, data):
        try:
            for field in ["description", "hsn_sac_code"]:
                if field in data and data[field]:
                    data[field] = normalize_text(data[field])

            line_item = LineItem(**data)

            validate_line_item(
                line_item,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            return data

        except (InvoiceValidationError, GSTValidationError):
            raise
        except Exception as e:
            logger.exception("Line item validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="line_item_validation_error",
            )

    def _apply_totals(self, instance):
        totals = calculate_line_item_total(instance)
        instance.total_amount = totals["total"]
        instance.cgst_amount = totals.get("cgst_amount", Decimal("0.00"))
        instance.sgst_amount = totals.get("sgst_amount", Decimal("0.00"))
        instance.igst_amount = totals.get("igst_amount", Decimal("0.00"))

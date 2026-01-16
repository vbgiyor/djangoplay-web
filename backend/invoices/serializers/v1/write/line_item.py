import logging

from django.db import transaction

from invoices.exceptions import InvoiceValidationError
from invoices.models.line_item import LineItem
from invoices.serializers.base import BaseLineItemSerializer

logger = logging.getLogger(__name__)


class LineItemWriteSerializer(BaseLineItemSerializer):

    """
    Write serializer for LineItem.
    """

    class Meta(BaseLineItemSerializer.Meta):
        read_only_fields = (
            "id",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        )

    @transaction.atomic
    def create(self, validated_data):
        try:
            item = LineItem(**validated_data)
            self._apply_totals(item)
            item.save()
            return item
        except Exception as e:
            logger.exception("LineItem creation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="line_item_create_failed",
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            self._apply_totals(instance)
            instance.save()
            return instance
        except Exception as e:
            logger.exception("LineItem update failed")
            raise InvoiceValidationError(
                message=str(e),
                code="line_item_update_failed",
            )

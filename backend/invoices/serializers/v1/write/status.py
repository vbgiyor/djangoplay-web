import logging

from django.db import transaction

from invoices.exceptions import InvalidInvoiceStatusError, InvoiceValidationError
from invoices.serializers.base import BaseStatusSerializer

logger = logging.getLogger(__name__)


class StatusWriteSerializer(BaseStatusSerializer):
    class Meta(BaseStatusSerializer.Meta):
        read_only_fields = ("id",)

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.is_locked:
            raise InvalidInvoiceStatusError(
                message="Cannot modify locked status",
                code="status_locked",
            )
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            logger.exception("Status update failed")
            raise InvoiceValidationError(
                message=str(e),
                code="status_update_failed",
            )

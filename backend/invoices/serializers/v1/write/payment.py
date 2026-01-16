import logging

from django.db import transaction

from invoices.exceptions import InvoiceValidationError
from invoices.models.payment import Payment
from invoices.serializers.base import BasePaymentSerializer
from invoices.services import update_invoice_status

logger = logging.getLogger(__name__)


class PaymentWriteSerializer(BasePaymentSerializer):
    class Meta(BasePaymentSerializer.Meta):
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        try:
            payment = Payment(**validated_data)
            payment.save()
            update_invoice_status(payment.invoice)
            return payment
        except Exception as e:
            logger.exception("Payment creation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_create_failed",
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            update_invoice_status(instance.invoice)
            return instance
        except Exception as e:
            logger.exception("Payment update failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_update_failed",
            )

import logging

from rest_framework import serializers

from invoices.exceptions import InvoiceValidationError
from invoices.models.payment import Payment
from invoices.services import (
    validate_payment_amount,
    validate_payment_reference,
)

logger = logging.getLogger(__name__)


class BasePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        try:
            payment = Payment(**data)

            validate_payment_amount(
                payment.amount,
                payment.invoice,
                self.instance.pk if self.instance else None,
            )

            validate_payment_reference(
                payment.payment_reference,
                payment.payment_method.code if payment.payment_method else None,
                payment.invoice,
                self.instance.pk if self.instance else None,
            )

            return data

        except InvoiceValidationError:
            raise
        except Exception as e:
            logger.exception("Payment validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_validation_error",
            )

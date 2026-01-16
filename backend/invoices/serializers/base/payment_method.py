import logging

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import InvoiceValidationError
from invoices.models.payment_method import PaymentMethod
from invoices.services.payment import validate_payment_method

logger = logging.getLogger(__name__)


class BasePaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        try:
            for field in ["code", "name", "description"]:
                if field in data and data[field]:
                    data[field] = normalize_text(data[field])

            pm = PaymentMethod(**data)

            validate_payment_method(
                pm,
                exclude_pk=self.instance.pk if self.instance else None,
            )

            return data

        except InvoiceValidationError:
            raise
        except Exception as e:
            logger.exception("Payment method validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_method_validation_error",
            )

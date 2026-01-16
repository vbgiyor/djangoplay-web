import logging

from django.db import transaction

from invoices.exceptions import InvoiceValidationError
from invoices.models.payment_method import PaymentMethod
from invoices.serializers.base import BasePaymentMethodSerializer

logger = logging.getLogger(__name__)


class PaymentMethodWriteSerializer(BasePaymentMethodSerializer):
    class Meta(BasePaymentMethodSerializer.Meta):
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        try:
            obj = PaymentMethod.objects.create(**validated_data)
            obj.save()
            return obj
        except Exception as e:
            logger.exception("PaymentMethod creation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_method_create_failed",
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            logger.exception("PaymentMethod update failed")
            raise InvoiceValidationError(
                message=str(e),
                code="payment_method_update_failed",
            )

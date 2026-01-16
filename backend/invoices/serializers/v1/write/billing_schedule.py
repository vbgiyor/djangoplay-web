import logging

from django.db import transaction

from invoices.exceptions import InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
from invoices.serializers.base import BaseBillingScheduleSerializer

logger = logging.getLogger(__name__)


class BillingScheduleWriteSerializer(BaseBillingScheduleSerializer):
    class Meta(BaseBillingScheduleSerializer.Meta):
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        try:
            obj = BillingSchedule.objects.create(**validated_data)
            obj.save()
            return obj
        except Exception as e:
            logger.exception("BillingSchedule creation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="billing_schedule_create_failed",
            )

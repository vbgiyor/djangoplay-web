import logging

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
from invoices.services import validate_billing_schedule

logger = logging.getLogger(__name__)


class BaseBillingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingSchedule
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        try:
            if "description" in data and data["description"]:
                data["description"] = normalize_text(data["description"])

            schedule = BillingSchedule(**data)

            validate_billing_schedule(
                schedule,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            return data

        except InvoiceValidationError:
            raise
        except Exception as e:
            logger.exception("Billing schedule validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="billing_schedule_validation_error",
            )

import logging

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import InvalidInvoiceStatusError, InvoiceValidationError
from invoices.models.status import Status
from invoices.services import validate_status

logger = logging.getLogger(__name__)


class BaseStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        try:
            for field in ["name", "code", "description"]:
                if field in data and data[field]:
                    data[field] = normalize_text(data[field])

            status = Status(**data)

            validate_status(
                status,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            return data

        except (InvoiceValidationError, InvalidInvoiceStatusError):
            raise
        except Exception as e:
            logger.exception("Status validation failed")
            raise InvoiceValidationError(
                message=str(e),
                code="status_validation_error",
            )

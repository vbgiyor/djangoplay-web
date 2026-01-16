import logging

from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from invoices.exceptions import GSTValidationError
from invoices.models.gst_configuration import GSTConfiguration
from invoices.services import validate_gst_configuration

logger = logging.getLogger(__name__)


class BaseGSTConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GSTConfiguration
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        try:
            if "description" in data and data["description"]:
                data["description"] = normalize_text(data["description"])

            gst = GSTConfiguration(**data)

            validate_gst_configuration(
                gst,
                exclude_pk=self.instance.pk if self.instance else None,
            )
            return data

        except GSTValidationError:
            raise
        except Exception as e:
            logger.exception("GST configuration validation failed")
            raise GSTValidationError(
                message=str(e),
                code="gst_validation_error",
            )

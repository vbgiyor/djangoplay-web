import logging

from django.db import transaction

from invoices.exceptions import GSTValidationError
from invoices.models.gst_configuration import GSTConfiguration
from invoices.serializers.base import BaseGSTConfigurationSerializer

logger = logging.getLogger(__name__)


class GSTConfigurationWriteSerializer(BaseGSTConfigurationSerializer):
    class Meta(BaseGSTConfigurationSerializer.Meta):
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        try:
            obj = GSTConfiguration.objects.create(**validated_data)
            obj.save()
            return obj
        except Exception as e:
            logger.exception("GSTConfiguration creation failed")
            raise GSTValidationError(
                message=str(e),
                code="gst_config_create_failed",
            )
